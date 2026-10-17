"""Render the Kokoro lines of one shard. Usage: python engines/kokoro_lines.py WORK A B OUTDIR
For each line in [A, B) whose character uses Kokoro: OUTDIR/<id>.wav (24 kHz) and OUTDIR/<id>.json
{"words": [start seconds of each whitespace word, relative to the wav]}."""
import json, os, sys
import numpy as np
import torch
from kokoro import KPipeline
from lexicon import mark
from script import work_parts, load_cast, word_starts, char_spec, speech_text
import subprocess, tempfile
from common import write_wav

torch.set_num_threads(os.cpu_count() or 4)
SR = 24000


def pitch(wav, semitones):
    """Shift pitch, keeping duration and formants (so word timings stay exact). Ages a voice without slowing it."""
    tmp = wav + ".tmp.wav"
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-af",
                        f"rubberband=pitch={2 ** (semitones / 12):.6f}:formant=preserved", tmp])
    if r.returncode == 0:
        os.replace(tmp, wav)
    else:
        print("WARNING: rubberband unavailable, pitch not applied", flush=True)


def main(work, a, b, out):
    os.makedirs(out, exist_ok=True)
    cast = load_cast(); speed = cast.get("speed", 0.92)
    flat = [l for p in work_parts(work) for l in p["lines"]][int(a):int(b)]
    todo = [l for l in flat if char_spec(cast, work, l["who"])["engine"] == "kokoro"]
    if not todo:
        return
    pipes = {"gb": KPipeline(lang_code="b", repo_id="hexgrad/Kokoro-82M"),
             "us": KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")}
    vcache = {}
    for n, l in enumerate(todo):
        c = char_spec(cast, work, l["who"]); acc = c.get("accent", "gb")
        vk = json.dumps(c["kokoro"])
        if vk not in vcache:
            vcache[vk] = sum(w * pipes["gb"].load_single_voice(v) for v, w in c["kokoro"])
        audio, toks, off = [], [], 0.0
        for r in pipes[acc](mark(speech_text(l["text"]), acc), voice=vcache[vk], speed=speed):
            if r.audio is None:
                continue
            x = r.audio.numpy()
            toks += [(t.text, None if t.start_ts is None else off + t.start_ts) for t in (r.tokens or [])]
            audio.append(x); off += len(x) / SR
        wav = f"{out}/{l['id']}.wav"
        write_wav(wav, np.concatenate(audio) if audio else np.zeros(SR // 10), SR)
        if c.get("pitch"):
            pitch(wav, c["pitch"])
        starts, miss = word_starts(l["text"], toks)
        json.dump({"words": starts, "interpolated": miss, "engine": "kokoro"}, open(f"{out}/{l['id']}.json", "w"))
        if n % 25 == 0:
            print(f"kokoro {work} {n}/{len(todo)}", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
