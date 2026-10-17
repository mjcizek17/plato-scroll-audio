"""Production renderer: one Plato work (all parts) with Kokoro, studio-mastered, with word timing.
Usage: python engines/kokoro_work.py KEY OUTDIR
Reads scripts/KEY.json and cast/cast.json. Writes per part:
  OUTDIR/KEY-pN.mp3          mono 24 kHz 64 kbps, -19 LUFS, true peak -3 dB
  OUTDIR/KEY-pN.timing.json  {entries: {entry: seconds}, words: {entry: [centiseconds per word]}}
                             (the read-along player's format; words are the whitespace tokens of the
                             entry text, footnote markers excluded)
  OUTDIR/KEY.report.json     durations, speakers, word coverage, unmatched words, speed
Pauses: 1.2 s after a heading or the opening line, 0.65 s at a change of speaker, 0.35 s between
passages by the same speaker. Room tone (~-66 dBFS pink noise) under everything instead of silence."""
import json, os, re, subprocess, sys, tempfile, time
import numpy as np
import torch
from kokoro import KPipeline
from lexicon import mark

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 24000
GAP = {"heading": 1.2, "change": 0.65, "same": 0.35}
NUMS = {"I": "One", "II": "Two", "III": "Three", "IV": "Four", "V": "Five", "VI": "Six", "VII": "Seven",
        "VIII": "Eight", "IX": "Nine", "X": "Ten", "XI": "Eleven", "XII": "Twelve"}
torch.set_num_threads(os.cpu_count() or 4)


def spoken(title):
    return re.sub(r"\b(XII|XI|X|IX|VIII|VII|VI|IV|V|III|II|I)\b", lambda m: NUMS[m.group(1).upper()], title, flags=re.I)


def norm(s):
    return re.sub(r"[^0-9a-z]", "", s.lower())


def word_starts(text, toks):
    """Start time of each whitespace word of `text`, from Kokoro tokens [(token_text, start)].
    Matches on letters/digits so punctuation and quote marks never shift the alignment."""
    words = text.split()
    owner = []  # for each alnum char of the text stream, the index of its word
    for wi, w in enumerate(words):
        owner += [wi] * len(norm(w))
    starts, pos, unmatched = [None] * len(words), 0, 0
    for tt, ts in toks:
        n = norm(tt)
        if not n:
            continue
        if pos < len(owner) and ts is not None:
            wi = owner[pos]
            if starts[wi] is None:
                starts[wi] = ts
        pos += len(n)
    # Fill words with no token (dashes, digits read differently) by interpolation.
    known = [i for i, s in enumerate(starts) if s is not None]
    for i in range(len(starts)):
        if starts[i] is None:
            unmatched += 1
            prev = max([k for k in known if k < i], default=None)
            nxt = min([k for k in known if k > i], default=None)
            if prev is not None and nxt is not None:
                starts[i] = starts[prev] + (starts[nxt] - starts[prev]) * (i - prev) / (nxt - prev)
            else:
                starts[i] = starts[prev] if prev is not None else (starts[nxt] if nxt is not None else 0.0)
    for i in range(1, len(starts)):  # monotonic
        starts[i] = max(starts[i], starts[i - 1])
    return starts, unmatched


def trim(a, thresh_db=-45, pad=0.04):
    env = np.convolve(np.abs(a), np.ones(240) / 240, mode="same")
    idx = np.where(env > 10 ** (thresh_db / 20))[0]
    if not len(idx):
        return a, 0
    s = max(0, idx[0] - int(pad * SR)); e = min(len(a), idx[-1] + int(pad * SR))
    return a[s:e], s


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


def main(key, out):
    os.makedirs(out, exist_ok=True)
    script = json.load(open(os.path.join(ROOT, "scripts", f"{key}.json"), encoding="utf-8"))
    cast = json.load(open(os.path.join(ROOT, "cast", "cast.json"), encoding="utf-8"))
    speed = cast.pop("speed", 0.92); cast.pop("_note", None)
    pipes = {"gb": KPipeline(lang_code="b", repo_id="hexgrad/Kokoro-82M"),
             "us": KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")}
    voices, missing = {}, set()

    def voice(who):
        if who not in voices:
            c = cast.get(who)
            if c is None:
                missing.add(who); c = cast["Narrator"]
            voices[who] = (sum(w * pipes["gb"].load_single_voice(v) for v, w in c["kokoro"]), c.get("accent", "gb"))
        return voices[who]

    def say(text, who):
        v, acc = voice(who)
        audio, toks, off = [], [], 0
        for r in pipes[acc](mark(text, acc), voice=v, speed=speed):
            if r.audio is None:
                continue
            a = r.audio.numpy()
            for t in r.tokens or []:
                toks.append((t.text, None if t.start_ts is None else off + t.start_ts))
            audio.append(a); off += len(a) / SR
        return (np.concatenate(audio) if audio else np.zeros(1, np.float32)), toks

    t0, report, rng = time.time(), {"key": key, "parts": []}, np.random.default_rng(7)
    nparts = len(script["parts"])
    for pi, part in enumerate(script["parts"]):
        lines = [dict(l) for l in part["lines"]]
        title = spoken(script["title"])
        if nparts == 1:
            opening = f"Plato's {title}, translated by David Horan."
        else:
            book = spoken(part["name"])
            opening = (f"Plato's {title}, translated by David Horan. {book}." if pi == 0 else f"Plato's {title}. {book}.")
            if lines and lines[0]["kind"] == "heading":
                lines = lines[1:]  # the book heading is spoken in the opening
        lines.insert(0, {"entry": None, "who": "Narrator", "text": opening, "kind": "heading"})

        pcm, t, entries, words, unmatched, nwords = [room_tone(int(0.6 * SR), rng)], 0.6, {}, {}, 0, 0
        for i, ln in enumerate(lines):
            a, toks = say(ln["text"], ln["who"])
            a, cut = trim(a)
            a = a + room_tone(len(a), rng)
            if ln["entry"] is not None:
                st, um = word_starts(ln["text"], [(x, None if s is None else s - cut / SR) for x, s in toks])
                e = str(ln["entry"])
                entries.setdefault(e, round(t, 2))
                words.setdefault(e, []).extend(int(round((t + max(0.0, s)) * 100)) for s in st)
                unmatched += um; nwords += len(st)
            pcm.append(a); t += len(a) / SR
            if i + 1 < len(lines):
                g = GAP["heading"] if ln["kind"] == "heading" else GAP["change" if lines[i + 1]["who"] != ln["who"] else "same"]
                pcm.append(room_tone(int(g * SR), rng)); t += g
            if i % 50 == 0:
                print(f"{key} p{pi + 1} line {i}/{len(lines)} {t / 60:.1f} min", flush=True)
        pcm.append(room_tone(int(1.5 * SR), rng)); t += 1.5
        name = f"{key}-p{pi + 1}"
        master(np.concatenate(pcm), os.path.join(out, f"{name}.mp3"))
        json.dump({"entries": entries, "words": words}, open(os.path.join(out, f"{name}.timing.json"), "w"),
                  separators=(",", ":"))
        report["parts"].append({"file": f"{name}.mp3", "minutes": round(t / 60, 2), "lines": len(lines),
                                "words": nwords, "words_interpolated": unmatched})
    wall = time.time() - t0
    audio = sum(p["minutes"] for p in report["parts"]) * 60
    report.update(speakers_without_cast=sorted(missing), wall_s=round(wall), x_realtime=round(audio / wall, 2))
    json.dump(report, open(os.path.join(out, f"{key}.report.json"), "w"), indent=1)
    print(json.dumps(report))


if __name__ == "__main__":
    main(*sys.argv[1:])
