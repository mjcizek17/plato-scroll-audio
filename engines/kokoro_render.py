"""Kokoro-82M (full precision) with the existing cast blends, British G2P, classicist lexicon.
Usage: python engines/kokoro_render.py OUTDIR
Writes OUTDIR/lines/NN.wav, OUTDIR/refs/<Character>.wav (+ .txt) for cloning engines, OUTDIR/speed.json."""
import os, re, sys
import torch
from kokoro import KPipeline
from common import load, write_wav, Timer

LEX = {  # traditional English classicist pronunciation, British phonemes
    "Socrates": "sˈɒkɹətiːz", "Alcibiades": "ˌælsɪbˈaɪədiːz", "Plato's": "plˈeɪtəʊz",
    "Plato": "plˈeɪtəʊ", "Horan": "hˈɒɹən",
}
SPEED = 0.92


def mark(text):
    for w, ipa in sorted(LEX.items(), key=lambda kv: -len(kv[0])):
        text = re.sub(rf"\b{re.escape(w)}(?![\w'])", f"[{w}](/{ipa}/)", text)
    return text


def main(out):
    passage, cast = load()
    pipe = KPipeline(lang_code="b", repo_id="hexgrad/Kokoro-82M")
    voices = {}
    for who, c in cast.items():
        voices[who] = sum(w * pipe.load_single_voice(v) for v, w in c["kokoro"])
    t = Timer("kokoro-82m-fp32")

    def say(text, who):
        chunks = [a for _, _, a in pipe(mark(text), voice=voices[who], speed=SPEED) if a is not None]
        return torch.cat(chunks).numpy()

    for i, ln in enumerate(passage["lines"]):
        t.add(write_wav(f"{out}/lines/{i:02d}.wav", say(ln["text"], ln["who"]), 24000))
    for who, c in cast.items():
        write_wav(f"{out}/refs/{who}.wav", say(c["ref_text"], who), 24000)
        open(f"{out}/refs/{who}.txt", "w").write(c["ref_text"])
    t.report(out)


if __name__ == "__main__":
    main(sys.argv[1])
