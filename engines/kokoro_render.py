"""Kokoro-82M (full precision) with the cast blends. Each character reads with his own accent's
pronunciation ('gb' British or 'us' American, from cast.json) so a voice never mixes the two.
Usage: python engines/kokoro_render.py OUTDIR
Writes OUTDIR/lines/NN.wav, OUTDIR/refs/<Character>.wav (+ .txt) for cloning engines, OUTDIR/speed.json,
and OUTDIR/options/<Character>.wav: numbered alternatives for any character with 'kokoro_options'."""
import os, re, sys
import numpy as np
import torch
from kokoro import KPipeline
from common import load, write_wav, Timer

LEX = {  # traditional English classicist pronunciation of names, per accent
    "gb": {"Socrates": "sˈɒkɹətiːz", "Alcibiades": "ˌælsɪbˈaɪədiːz", "Plato's": "plˈeɪtəʊz",
           "Plato": "plˈeɪtəʊ", "Horan": "hˈɒɹən", "Pericles": "pˈɛɹɪkliːz"},
    "us": {"Socrates": "sˈɑkɹətiz", "Alcibiades": "ˌælsəbˈaɪədiz", "Plato's": "plˈeɪtoʊz",
           "Plato": "plˈeɪtoʊ", "Horan": "hˈɔɹən", "Pericles": "pˈɛɹəkliz"},
}
SPEED = 0.92
NUM = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]


def mark(text, accent):
    for w, ipa in sorted(LEX[accent].items(), key=lambda kv: -len(kv[0])):
        text = re.sub(rf"\b{re.escape(w)}(?![\w'])", f"[{w}](/{ipa}/)", text)
    return text


def main(out):
    passage, cast = load()
    pipes = {"gb": KPipeline(lang_code="b", repo_id="hexgrad/Kokoro-82M"),
             "us": KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")}
    blend = lambda spec: sum(w * pipes["gb"].load_single_voice(v) for v, w in spec)
    voices = {who: blend(c["kokoro"]) for who, c in cast.items()}
    accent = {who: c.get("accent", "gb") for who, c in cast.items()}
    t = Timer("kokoro-82m-fp32")

    def say(text, voice, acc):
        return torch.cat([a for _, _, a in pipes[acc](mark(text, acc), voice=voice, speed=SPEED) if a is not None]).numpy()

    for i, ln in enumerate(passage["lines"]):
        who = ln["who"]
        t.add(write_wav(f"{out}/lines/{i:02d}.wav", say(ln["text"], voices[who], accent[who]), 24000))
    for who, c in cast.items():
        write_wav(f"{out}/refs/{who}.wav", say(c["ref_text"], voices[who], accent[who]), 24000)
        open(f"{out}/refs/{who}.txt", "w").write(c["ref_text"])
        if c.get("ref_text_long"):
            write_wav(f"{out}/refs/{who}-long.wav", say(c["ref_text_long"], voices[who], accent[who]), 24000)
    t.report(out)

    # Numbered options: an announcer (a female voice no character uses) says "Option one", then the
    # character reads his own lines from the passage in that voice.
    ann = pipes["gb"].load_single_voice("bf_emma")
    for who, c in cast.items():
        opts = c.get("kokoro_options")
        if not opts:
            continue
        mine = " ".join(l["text"] for l in passage["lines"] if l["who"] == who)[:600]
        pcm, sheet = [], []
        for n, v in enumerate(opts):
            pcm += [say(f"Option {NUM[n]}.", ann, "gb"), np.zeros(9600, np.float32),
                    say(mine, pipes["gb"].load_single_voice(v), accent[who]), np.zeros(24000, np.float32)]
            sheet.append(f"{n + 1}: {v}")
        write_wav(f"{out}/options/{who}.wav", np.concatenate(pcm), 24000)
        open(f"{out}/options/{who}.txt", "w").write("\n".join(sheet))


if __name__ == "__main__":
    main(sys.argv[1])
