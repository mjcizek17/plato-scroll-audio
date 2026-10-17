"""Make any missing Chatterbox reference clips that are defined from Kokoro (cast entry 'ref_kokoro').
Usage: python tools/make_refs.py   (needs kokoro; writes cast/refs/<ref>.wav and .txt)"""
import json, os, subprocess, sys
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engines"))
from common import write_wav  # noqa: E402
from lexicon import mark  # noqa: E402

cast = json.load(open(os.path.join(ROOT, "cast", "cast.json")))
todo = {c["ref"]: c["ref_kokoro"] for c in cast["characters"].values()
        if c.get("ref_kokoro") and not os.path.exists(os.path.join(ROOT, "cast", "refs", c["ref"] + ".wav"))}
if todo:
    from kokoro import KPipeline
    pipes = {}
    for name, rk in todo.items():
        acc = rk.get("accent", "gb")
        pipe = pipes.setdefault(acc, KPipeline(lang_code="b" if acc == "gb" else "a", repo_id="hexgrad/Kokoro-82M"))
        voice = sum(w * pipe.load_single_voice(v) for v, w in rk["voice"])
        audio = np.concatenate([r.audio.numpy() for r in pipe(mark(rk["text"], acc), voice=voice, speed=cast.get("speed", 0.92))
                                if r.audio is not None])
        out = os.path.join(ROOT, "cast", "refs", name + ".wav")
        write_wav(out, audio, 24000)
        if rk.get("pitch"):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", out, "-af",
                            f"rubberband=pitch={2 ** (rk['pitch'] / 12):.6f}:formant=preserved", out + ".p.wav"], check=True)
            os.replace(out + ".p.wav", out)
        open(os.path.join(ROOT, "cast", "refs", name + ".txt"), "w").write(rk["text"])
        print("made", name)
print("refs ok:", sorted(todo) or "none needed")
