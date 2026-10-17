"""Qwen3-TTS: cast each character from a written brief (VoiceDesign 1.7B), then perform every line with
the Base 1.7B model cloning that designed voice, so a character sounds the same in every line.
Usage: python engines/qwen_render.py OUTDIR
Writes OUTDIR/refs/<Character>.wav (+ .txt), OUTDIR/lines/NN.wav, OUTDIR/speed.json."""
import gc, os, sys
import torch
from qwen_tts import Qwen3TTSModel
from common import load, write_wav, Timer

torch.set_num_threads(os.cpu_count() or 4)
KW = dict(device_map="cpu", dtype=torch.float32)


def main(out):
    passage, cast = load()
    t = Timer("qwen3-tts-1.7b design+clone")
    design = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign", **KW)
    for who, c in cast.items():
        torch.manual_seed(1234)
        wavs, sr = design.generate_voice_design(text=c["ref_text"], language="English", instruct=c["design"])
        write_wav(f"{out}/refs/{who}.wav", wavs[0], sr)
        open(f"{out}/refs/{who}.txt", "w").write(c["ref_text"])
        print("designed", who, flush=True)
    del design; gc.collect()

    clone = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-Base", **KW)
    prompts = {who: clone.create_voice_clone_prompt(ref_audio=f"{out}/refs/{who}.wav", ref_text=c["ref_text"])
               for who, c in cast.items()}
    for i, ln in enumerate(passage["lines"]):
        torch.manual_seed(1234 + i)
        wavs, sr = clone.generate_voice_clone(text=ln["text"], language="English", voice_clone_prompt=prompts[ln["who"]])
        t.add(write_wav(f"{out}/lines/{i:02d}.wav", wavs[0], sr))
        print("line", i, flush=True)
    t.report(out)


if __name__ == "__main__":
    main(sys.argv[1])
