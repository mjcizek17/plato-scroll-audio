"""Chatterbox (Resemble AI, MIT) performing lines by cloning a Kokoro reference clip per character.
Usage: python engines/chatterbox_render.py KOKORO_DIR OUTDIR MODE
KOKORO_DIR is the Kokoro audition output (lines/NN.wav and refs/<Character>[-long].wav).
MODE:
  all           every character in Chatterbox (audition sample 4)
  keep-alc      Socrates and Narrator in Chatterbox; Alcibiades' lines are the Kokoro takes unchanged
  alc-long      every character in Chatterbox; Alcibiades cloned from a longer reference, less exaggeration"""
import os, shutil, sys
import torch
from common import load, write_wav, Timer

torch.set_num_threads(os.cpu_count() or 4)


def main(kdir, out, mode="all"):
    passage, cast = load()
    from chatterbox.tts import ChatterboxTTS
    model = ChatterboxTTS.from_pretrained(device="cpu")
    t = Timer(f"chatterbox-{mode}")
    os.makedirs(f"{out}/lines", exist_ok=True)
    for i, ln in enumerate(passage["lines"]):
        who = ln["who"]
        if mode == "keep-alc" and who == "Alcibiades":
            shutil.copy(f"{kdir}/lines/{i:02d}.wav", f"{out}/lines/{i:02d}.wav"); continue
        ref, ex = f"{kdir}/refs/{who}.wav", cast[who].get("exaggeration", 0.5)
        if mode == "alc-long" and who == "Alcibiades":
            ref, ex = f"{kdir}/refs/{who}-long.wav", 0.45
        torch.manual_seed(1234 + i)
        wav = model.generate(ln["text"], audio_prompt_path=ref, exaggeration=ex, cfg_weight=0.5)
        t.add(write_wav(f"{out}/lines/{i:02d}.wav", wav.squeeze().cpu().numpy(), model.sr))
        print("line", i, flush=True)
    t.report(out)


if __name__ == "__main__":
    main(*sys.argv[1:])
