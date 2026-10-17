"""Chatterbox (Resemble AI, MIT): performs each line cloning a reference clip per character.
Usage: python engines/chatterbox_render.py REFDIR OUTDIR [turbo]
REFDIR holds <Character>.wav from another engine (the Kokoro cast or the Qwen-designed cast)."""
import os, sys
import torch
from common import load, write_wav, Timer

torch.set_num_threads(os.cpu_count() or 4)


def main(refs, out, variant="original"):
    passage, cast = load()
    if variant == "turbo":
        from chatterbox.tts_turbo import ChatterboxTurboTTS as M
    else:
        from chatterbox.tts import ChatterboxTTS as M
    model = M.from_pretrained(device="cpu")
    t = Timer(f"chatterbox-{variant}")
    for i, ln in enumerate(passage["lines"]):
        torch.manual_seed(1234 + i)
        kw = dict(audio_prompt_path=f"{refs}/{ln['who']}.wav")
        if variant != "turbo":
            kw.update(exaggeration=cast[ln["who"]].get("exaggeration", 0.5), cfg_weight=0.5)
        wav = model.generate(ln["text"], **kw)
        t.add(write_wav(f"{out}/lines/{i:02d}.wav", wav.squeeze().cpu().numpy(), model.sr))
        print("line", i, flush=True)
    t.report(out)


if __name__ == "__main__":
    main(*sys.argv[1:])
