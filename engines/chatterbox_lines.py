"""Render the Chatterbox lines of one shard. Usage: python engines/chatterbox_lines.py WORK A B OUTDIR
Each line is performed in sentence groups of <= 300 characters (the model's comfortable length), each
group checked for runaway or truncated takes by its duration and re-taken with a new seed if needed.
Word timing comes from forced alignment of the finished line against its text (torchaudio MMS_FA).
Writes OUTDIR/<id>.wav (24 kHz) and OUTDIR/<id>.json {"words": [...], "retakes": n, ...}."""
import json, os, re, sys, zlib
import numpy as np
import torch, torchaudio
from script import work_parts, load_cast, fill
from common import write_wav

torch.set_num_threads(os.cpu_count() or 4)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CPS = 15.5          # expected characters per second of speech (from the audition takes)
MAXC = 300


def groups(text):
    sents = re.split(r"(?<=[.!?;:])[\"”’)]*\s+", text)
    out, cur = [], ""
    for s in sents:
        if len(s) > MAXC and cur:
            out.append(cur); cur = ""
        while len(s) > MAXC:  # very long sentence: break at a comma (else a space) near the limit
            k = s.rfind(", ", 0, MAXC)
            k = k + 1 if k > MAXC // 3 else s.rfind(" ", 0, MAXC)
            out.append(s[:k].strip()); s = s[k:].strip()
        if len(cur) + len(s) + 1 > MAXC and cur:
            out.append(cur); cur = s
        else:
            cur = (cur + " " + s).strip()
    return out + ([cur] if cur else [])


def speakable(t):
    t = t.replace("—", ", ").replace("–", ", ").replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    return re.sub(r"\s+", " ", t).strip()


def trim(a, sr, db=-45, pad=0.03):
    env = np.convolve(np.abs(a), np.ones(240) / 240, mode="same")
    idx = np.where(env > 10 ** (db / 20))[0]
    if not len(idx):
        return a
    return a[max(0, idx[0] - int(pad * sr)): idx[-1] + int(pad * sr)]


class Aligner:
    def __init__(self):
        b = torchaudio.pipelines.MMS_FA
        self.model, self.tok, self.align, self.sr = b.get_model(), b.get_tokenizer(), b.get_aligner(), b.sample_rate

    def __call__(self, audio, sr, text):
        words = text.split()
        clean = [re.sub(r"[^a-z]", "", w.lower()) for w in words]
        keep = [i for i, w in enumerate(clean) if w]
        starts = [None] * len(words)
        if keep:
            wav = torchaudio.functional.resample(torch.tensor(audio).unsqueeze(0), sr, self.sr)
            with torch.inference_mode():
                em, _ = self.model(wav)
                spans = self.align(em[0], self.tok([clean[i] for i in keep]))
            ratio = wav.size(1) / em.size(1) / self.sr
            for i, sp in zip(keep, spans):
                starts[i] = sp[0].start * ratio
        return fill(starts)


def main(work, a, b, out):
    os.makedirs(out, exist_ok=True)
    cast = load_cast()
    flat = [l for p in work_parts(work) for l in p["lines"]][int(a):int(b)]
    todo = [l for l in flat if cast["characters"].get(l["who"], cast["characters"]["Narrator"])["engine"] == "chatterbox"]
    if not todo:
        return
    from chatterbox.tts import ChatterboxTTS
    model = ChatterboxTTS.from_pretrained(device="cpu"); sr = model.sr
    align = Aligner()
    for n, l in enumerate(todo):
        c = cast["characters"].get(l["who"], cast["characters"]["Narrator"])
        ref = os.path.join(ROOT, "cast", "refs", c["ref"] + ".wav")
        pcm, retakes, flags = [], 0, []
        for gi, g in enumerate(groups(l["text"])):
            want, best = len(g) / CPS, None
            for attempt in range(3):
                torch.manual_seed(zlib.crc32(f"{work}{l['id']}{gi}{attempt}".encode()))
                x = trim(model.generate(speakable(g), audio_prompt_path=ref, exaggeration=c.get("exaggeration", 0.5),
                                        cfg_weight=c.get("cfg", 0.5)).squeeze().cpu().numpy(), sr)
                r = (len(x) / sr) / max(want, 0.4)
                if best is None or abs(np.log(r)) < abs(np.log(best[1])):
                    best = (x, r)
                if 0.6 <= r <= 1.6:
                    break
                retakes += 1
            if not 0.6 <= best[1] <= 1.6:
                flags.append({"group": gi, "ratio": round(best[1], 2), "text": g[:80]})
            if pcm:
                pcm.append(np.zeros(int(0.28 * sr), np.float32))
            pcm.append(best[0].astype(np.float32))
        audio = np.concatenate(pcm)
        write_wav(f"{out}/{l['id']}.wav", audio, sr)
        starts, miss = align(audio, sr, l["text"])
        json.dump({"words": starts, "interpolated": miss, "retakes": retakes, "flags": flags, "engine": "chatterbox"},
                  open(f"{out}/{l['id']}.json", "w"))
        print(f"chatterbox {work} {n + 1}/{len(todo)} {l['id']} retakes={retakes}", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
