"""Audition reader voices on a passage: one numbered MP3 per candidate, "Option N" announced first.
Usage: python tools/audition_voice.py audition/<name>.json OUTDIR
The JSON: {"passage": "...", "ref_text": "...", "candidates": [{"name", "kokoro": [[voice, weight]...], "accent",
"pitch", "exaggeration", "engine": "chatterbox"|"kokoro"}...]}. Chatterbox candidates clone a Kokoro clip of ref_text
(pitched as asked, like tools/make_refs.py); Kokoro candidates read directly. Writes OUTDIR/option-N.mp3 and sheet.txt."""
import json, os, re, subprocess, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engines"))
sys.path.insert(0, os.path.join(ROOT, "text"))
from common import write_wav  # noqa: E402
from lexicon import mark  # noqa: E402
from script import speech_text  # noqa: E402
import notes  # noqa: E402

NUM = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]
SR = 24000


def pitch(path, semitones):
    if not semitones:
        return
    tmp = path + ".p.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-af",
                    f"rubberband=pitch={2 ** (semitones / 12):.6f}:formant=preserved", tmp], check=True)
    os.replace(tmp, path)


def master(wav, mp3):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-af",
                    "highpass=f=70,acompressor=threshold=-20dB:ratio=2:attack=15:release=200,loudnorm=I=-19:TP=-3",
                    "-ar", "44100", "-b:a", "96k", mp3], check=True)


def main(spec_path, out):
    spec = json.load(open(spec_path))
    os.makedirs(out, exist_ok=True)
    from kokoro import KPipeline
    pipes = {"gb": KPipeline(lang_code="b", repo_id="hexgrad/Kokoro-82M"),
             "us": KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")}
    speed = spec.get("speed", 0.92)

    def kokoro_say(text, blend, acc):
        voice = sum(w * pipes["gb"].load_single_voice(v) for v, w in blend)
        return np.concatenate([r.audio.numpy() for r in pipes[acc](mark(text, acc), voice=voice, speed=speed) if r.audio is not None])

    passage = speech_text(notes.spoken(spec["passage"]))
    announcer = [["bf_emma", 1.0]]
    model = None
    sheet = []
    for n, c in enumerate(spec["candidates"]):
        acc = c.get("accent", "gb")
        ref = os.path.join(out, f"ref-{n + 1}.wav")
        write_wav(ref, kokoro_say(spec["ref_text"], c["kokoro"], acc), SR)
        pitch(ref, c.get("pitch", 0))
        if c.get("engine", "chatterbox") == "chatterbox":
            if model is None:
                import torch
                from chatterbox.tts import ChatterboxTTS
                torch.set_num_threads(os.cpu_count() or 4)
                model = ChatterboxTTS.from_pretrained(device="cpu")
            parts = []
            for sent_group in re.split(r"(?<=[.!?])\s+(?=[A-Z“])", passage):
                if not sent_group.strip():
                    continue
                import torch
                torch.manual_seed(100 + n)
                w = model.generate(sent_group, audio_prompt_path=ref, exaggeration=c.get("exaggeration", 0.4), cfg_weight=0.5)
                parts.append(w.squeeze().cpu().numpy()); parts.append(np.zeros(int(0.3 * model.sr), np.float32))
            audio = np.concatenate(parts); sr = model.sr
        else:
            audio = kokoro_say(passage, c["kokoro"], acc); sr = SR
            if c.get("pitch"):
                tmp = os.path.join(out, f"line-{n + 1}.wav"); write_wav(tmp, audio, sr); pitch(tmp, c["pitch"])
                audio = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", tmp, "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"],
                                                     capture_output=True, check=True).stdout, dtype=np.float32)
        ann = kokoro_say(f"Option {NUM[n]}.", announcer, "gb")
        if sr != SR:
            ann = np.interp(np.arange(0, len(ann) * sr / SR) * SR / sr, np.arange(len(ann)), ann).astype(np.float32)
        wav = os.path.join(out, f"option-{n + 1}.wav")
        write_wav(wav, np.concatenate([ann, np.zeros(int(0.6 * sr), np.float32), audio]), sr)
        master(wav, os.path.join(out, f"option-{n + 1}.mp3"))
        os.remove(wav)
        sheet.append(f"{n + 1}. {c['name']}")
        print("done", n + 1, c["name"], flush=True)
    open(os.path.join(out, "sheet.txt"), "w").write("\n".join(sheet) + "\n")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
