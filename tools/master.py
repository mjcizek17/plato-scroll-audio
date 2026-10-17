"""Studio-style assembly of per-line WAVs into one finished MP3.
Usage: python tools/master.py LINESDIR passage.json OUT.mp3 [--kbps 128]

Per line: trim the engine's own leading/trailing silence, 70 Hz high-pass, gentle 2:1 compression.
Between lines: room tone (very quiet pink noise, ~-66 dBFS) instead of digital silence, which on
headphones is the tell-tale sign of synthetic audio. Pauses: 1.4 s after the title, 0.65 s at a
change of speaker, 0.35 s between passages by the same speaker. Whole file: loudness -19 LUFS,
true peak -3 dB (audiobook-distributor range), 44.1 kHz mono MP3."""
import json, os, subprocess, sys, tempfile
import numpy as np

SR = 44100
LINE_FX = ("silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.02,"
           "areverse,silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.05,areverse,"
           "highpass=f=70,acompressor=threshold=-20dB:ratio=2:attack=15:release=200:makeup=1")
GAP = {"title": 1.4, "change": 0.65, "same": 0.35}


def ff_read(path, fx):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-af", fx, "-ac", "1", "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def room_tone(secs, rng, n=None):
    n = int(round(secs * SR)) if n is None else n
    white = rng.standard_normal(n + 64).astype(np.float32)
    pink = np.convolve(white, np.ones(32) / 32, mode="same")[:n]  # soft, dark noise floor
    pink /= (np.sqrt(np.mean(pink ** 2)) + 1e-9)
    return pink * 10 ** (-66 / 20)


def main(lines_dir, passage_path, out, kbps="128"):
    lines = json.load(open(passage_path, encoding="utf-8"))["lines"]
    rng = np.random.default_rng(7)
    parts, starts, t = [room_tone(0.5, rng)], [], 0.5
    for i, ln in enumerate(lines):
        a = ff_read(os.path.join(lines_dir, f"{i:02d}.wav"), LINE_FX)
        a = a + room_tone(0, rng, n=len(a))
        starts.append(round(t, 2)); parts.append(a); t += len(a) / SR
        if i + 1 < len(lines):
            g = GAP["title"] if ln["entry"] == "title" else GAP["change" if lines[i + 1]["who"] != ln["who"] else "same"]
            parts.append(room_tone(g, rng)); t += g
    parts.append(room_tone(1.0, rng))
    pcm = np.concatenate(parts).astype(np.float32)
    with tempfile.NamedTemporaryFile(suffix=".f32") as f:
        f.write(pcm.tobytes()); f.flush()
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", f.name,
                        "-af", "loudnorm=I=-19:TP=-3:LRA=9", "-ar", str(SR), "-b:a", f"{kbps}k", out], check=True)
    json.dump({"starts": starts}, open(os.path.splitext(out)[0] + ".starts.json", "w"))
    print(out, round(t, 1), "s")


if __name__ == "__main__":
    a = sys.argv[1:]
    kb = a[a.index("--kbps") + 1] if "--kbps" in a else "128"
    a = [x for x in a if x not in ("--kbps", kb)]
    main(*a, kbps=kb)
