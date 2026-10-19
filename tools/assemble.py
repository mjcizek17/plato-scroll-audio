"""Assemble one work from its rendered lines into finished, mastered parts with read-along timing.
Usage: python tools/assemble.py WORK LINESDIR OUTDIR
Per line: trim the take's own edges, level-match speech to -20 dBFS so Kokoro and Chatterbox voices sit
together, room tone underneath. Pauses: 1.2 s after a heading/opening, 0.65 s at a change of speaker,
0.35 s between passages by the same speaker, 0.25 s at a voice change inside one paragraph. Whole part: 70 Hz high-pass, gentle 2:1 compression,
-19 LUFS, true peak -3 dB; MP3 mono 24 kHz 64 kbps.
Writes OUTDIR/WORK-pN.mp3, OUTDIR/WORK-pN.timing.json ({entries:{entry:s}, words:{entry:[cs]}}),
OUTDIR/WORK.report.json. Exits non-zero if any line is missing."""
import json, os, subprocess, sys, tempfile, wave
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "engines"))
from script import work_parts  # noqa: E402

SR = 24000
GAP = {"heading": 1.2, "change": 0.65, "same": 0.35, "within": 0.25}


def read_wav(p):
    with wave.open(p) as w:
        sr, x = w.getframerate(), np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768
    if sr != SR:
        x = np.interp(np.arange(0, len(x), sr / SR), np.arange(len(x)), x).astype(np.float32)
    return x


def trim(a, db=-45, pad=0.04):
    env = np.convolve(np.abs(a), np.ones(240) / 240, mode="same")
    idx = np.where(env > 10 ** (db / 20))[0]
    if not len(idx):
        return a, 0
    s = max(0, idx[0] - int(pad * SR))
    return a[s: idx[-1] + int(pad * SR)], s


def level(a, target_db=-20.0):
    fr = a[: len(a) // 480 * 480].reshape(-1, 480)
    rms = np.sqrt(np.mean(fr ** 2, axis=1) + 1e-12)
    act = rms[rms > 10 ** (-40 / 20)]
    if not len(act):
        return a
    g = np.clip(target_db - 20 * np.log10(np.sqrt(np.mean(act ** 2))), -12, 12)
    return a * 10 ** (g / 20)


def room_tone(n, rng):
    w = rng.standard_normal(n + 64).astype(np.float32)
    p = np.convolve(w, np.ones(32) / 32, mode="same")[:n]
    return (p / (np.sqrt(np.mean(p ** 2)) + 1e-9) * 10 ** (-66 / 20)).astype(np.float32)


def master(pcm, out):
    with tempfile.NamedTemporaryFile(suffix=".f32") as f:
        f.write(pcm.astype(np.float32).tobytes()); f.flush()
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", f.name,
                        "-af", "highpass=f=70,acompressor=threshold=-20dB:ratio=2:attack=15:release=200,"
                        "loudnorm=I=-19:TP=-3:LRA=9", "-ar", str(SR), "-b:a", "64k", out], check=True)


def main(work, lines_dir, out):
    os.makedirs(out, exist_ok=True)
    parts = work_parts(work)
    missing = [l["id"] for p in parts for l in p["lines"] if not os.path.exists(os.path.join(lines_dir, l["id"] + ".wav"))]
    if missing:
        print("MISSING", len(missing), missing[:20]); sys.exit(1)
    rng, report = np.random.default_rng(7), {"work": work, "parts": []}
    for pi, p in enumerate(parts):
        lines = p["lines"]
        pcm, t, entries, words = [room_tone(int(0.6 * SR), rng)], 0.6, {}, {}
        interp = nwords = retakes = 0; flags = []
        for i, l in enumerate(lines):
            a, cut = trim(read_wav(os.path.join(lines_dir, l["id"] + ".wav")))
            a = level(a)
            a = a + room_tone(len(a), rng)
            meta = json.load(open(os.path.join(lines_dir, l["id"] + ".json")))
            if l["entry"] is not None:
                e = str(l["entry"])
                entries.setdefault(e, round(t, 2))
                ws = [int(round((t + max(0.0, s - cut / SR)) * 100)) for s in meta["words"]]
                # words shown in the reader but not read (a speaker label "Socrates:") light with the first word read
                words.setdefault(e, []).extend([ws[0] if ws else int(round(t * 100))] * l.get("skip", 0) + ws)
                interp += meta.get("interpolated", 0); nwords += len(meta["words"])
            retakes += meta.get("retakes", 0)
            flags += [dict(f, line=l["id"]) for f in meta.get("flags", [])]
            pcm.append(a); t += len(a) / SR
            if i + 1 < len(lines):
                nx = lines[i + 1]
                if l["kind"] == "heading":
                    g = GAP["heading"]
                elif l["entry"] is not None and nx["entry"] == l["entry"]:
                    g = GAP["within"]  # a voice change inside one paragraph: "said he," / "Well…"
                else:
                    g = GAP["change" if nx["who"] != l["who"] else "same"]
                pcm.append(room_tone(int(g * SR), rng)); t += g
        pcm.append(room_tone(int(1.5 * SR), rng)); t += 1.5
        name = f"{work}-p{pi + 1}"
        master(np.concatenate(pcm), os.path.join(out, name + ".mp3"))
        json.dump({"entries": entries, "words": words}, open(os.path.join(out, name + ".timing.json"), "w"),
                  separators=(",", ":"))
        report["parts"].append({"file": name + ".mp3", "minutes": round(t / 60, 2), "lines": len(lines), "words": nwords,
                                "words_interpolated": interp, "retakes": retakes, "flagged_takes": flags})
    json.dump(report, open(os.path.join(out, work + ".report.json"), "w"), indent=1)
    print(json.dumps(report)[:2000])


if __name__ == "__main__":
    main(*sys.argv[1:])
