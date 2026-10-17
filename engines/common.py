"""Shared helpers for every engine: load the passage and cast, time the render, write per-line WAVs."""
import json, os, sys, time, wave
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(passage="audition/passage.json", cast="audition/cast.json"):
    p = json.load(open(os.path.join(ROOT, passage), encoding="utf-8"))
    c = json.load(open(os.path.join(ROOT, cast), encoding="utf-8"))
    c.pop("_note", None)
    return p, c


def write_wav(path, audio, sr):
    a = np.asarray(audio, dtype=np.float32).flatten()
    a = np.clip(a, -1, 1)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(int(sr))
        w.writeframes((a * 32767).astype("<i2").tobytes())
    return len(a) / sr


class Timer:
    """Records wall time vs audio seconds so we can plan the full-corpus run (real-time factor)."""

    def __init__(self, name):
        self.name, self.audio, self.t0 = name, 0.0, time.time()

    def add(self, secs):
        self.audio += secs

    def report(self, outdir):
        wall = time.time() - self.t0
        r = {"engine": self.name, "audio_s": round(self.audio, 1), "wall_s": round(wall, 1),
             "x_realtime": round(self.audio / wall, 3) if wall else None, "cpus": os.cpu_count()}
        os.makedirs(outdir, exist_ok=True)
        json.dump(r, open(os.path.join(outdir, "speed.json"), "w"), indent=1)
        print(json.dumps(r))
