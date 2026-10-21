"""Patch a published work: re-recorded paragraphs are spliced into the existing MP3s, and the read-along timing is
corrected, without recording the whole work again.
Usage: python tools/patch.py WORK LINESDIR PUBDIR OUTDIR ENTRIES
  LINESDIR  the new takes (pNlNNNN.wav + .json) of every line belonging to the patched entries (paragraphs)
  PUBDIR    the published WORK-pN.mp3 and WORK-pN.timing.json
  ENTRIES   comma-separated entry (paragraph) numbers, as in the book
For each patched paragraph: the old audio runs from its start (timing "entries") to the silence that follows its last
word; that stretch is replaced by the new takes (trimmed, levelled, joined with the usual pauses, filtered like the
master and matched in loudness to the speech it replaces); the pause after it is kept. Every later timestamp moves by
the difference. Untouched audio is only decoded and re-encoded (MP3 mono 24 kHz 64 kbps, no further processing).
Writes OUTDIR/WORK-pN.mp3 + .timing.json for each changed part and OUTDIR/WORK.patch-report.json."""
import json, os, subprocess, sys, tempfile
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from assemble import SR, GAP, read_wav, trim, level, room_tone  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "engines"))
from script import work_parts  # noqa: E402


def decode(mp3):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", mp3, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def encode(pcm, out):
    with tempfile.NamedTemporaryFile(suffix=".f32") as f:
        f.write(pcm.astype(np.float32).tobytes()); f.flush()
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", f.name,
                        "-ar", str(SR), "-b:a", "64k", out], check=True)


def chain(pcm):
    """the master's filters without loudnorm (loudness is matched to the surrounding speech instead)"""
    with tempfile.NamedTemporaryFile(suffix=".f32") as f:
        f.write(pcm.astype(np.float32).tobytes()); f.flush()
        raw = subprocess.run(["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", f.name, "-af",
                              "highpass=f=70,acompressor=threshold=-20dB:ratio=2:attack=15:release=200",
                              "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def frames_db(x, hop=240):
    n = len(x) // hop
    fr = x[: n * hop].reshape(n, hop)
    return 20 * np.log10(np.sqrt(np.mean(fr ** 2, axis=1)) + 1e-9)


def active_rms(x):
    db = frames_db(x)
    if not len(db):
        return None
    thr = max(np.percentile(db, 95) - 25, -50)
    act = db[db > thr]
    return 10 ** (np.mean(act) / 20) if len(act) else None


def speech_end(pcm, t_from, t_limit, floor_db):
    """time where the speech after t_from stops: the first 0.2 s run of frames near the noise floor"""
    hop = 240; db = frames_db(pcm)
    i0, i1 = int(t_from * SR / hop), min(len(db), int(t_limit * SR / hop))
    need, run = int(0.2 * SR / hop), 0
    for i in range(i0, i1):
        run = run + 1 if db[i] < floor_db else 0
        if run >= need:
            return (i - need + 1) * hop / SR
    return t_limit


def main(work, lines_dir, pub, out, entries):
    os.makedirs(out, exist_ok=True)
    want = {int(e) for e in entries.split(",") if e.strip()}
    rng, report = np.random.default_rng(11), {"work": work, "patched": []}
    for pi, p in enumerate(work_parts(work)):
        name = f"{work}-p{pi + 1}"
        mine = sorted({l["entry"] for l in p["lines"] if l["entry"] in want})
        if not mine:
            continue
        pcm = decode(os.path.join(pub, name + ".mp3"))
        tm = json.load(open(os.path.join(pub, name + ".timing.json")))
        ent = {int(k): v for k, v in tm["entries"].items()}
        words = {int(k): v for k, v in tm["words"].items()}
        floor = np.percentile(frames_db(pcm), 10) + 10
        for e in sorted(mine, reverse=True):              # from the end, so earlier offsets stay valid while splicing
            if e not in ent:
                print("no timing for entry", e); continue
            start = ent[e]
            later = sorted(v for k, v in ent.items() if v > start)
            limit = later[0] if later else len(pcm) / SR - 1.0
            last_word = (max(words.get(e, [0])) / 100) if words.get(e) else start
            end = speech_end(pcm, max(start, last_word) + 0.05, limit, floor)
            lines = [l for l in p["lines"] if l["entry"] == e]
            seg, segw, t = [], [], 0.0
            for li, l in enumerate(lines):
                a, cut = trim(read_wav(os.path.join(lines_dir, l["id"] + ".wav")))
                a = level(a); a = a + room_tone(len(a), rng)
                meta = json.load(open(os.path.join(lines_dir, l["id"] + ".json")))
                ws = [int(round((t + max(0.0, s - cut / SR)) * 100)) for s in meta["words"]]
                segw += [ws[0] if ws else int(round(t * 100))] * l.get("skip", 0) + ws
                seg.append(a); t += len(a) / SR
                if li + 1 < len(lines):
                    g = GAP["heading"] if l["kind"] == "heading" else GAP["within"] if lines[li + 1]["who"] != l["who"] else GAP["same"]
                    seg.append(room_tone(int(g * SR), rng)); t += g
            new = chain(np.concatenate(seg))
            old = pcm[int(start * SR): int(end * SR)]
            ro, rn = active_rms(old), active_rms(new)
            if ro and rn:
                new = new * (ro / rn)
            delta = len(new) / SR - (end - start)
            pcm = np.concatenate([pcm[: int(start * SR)], new.astype(np.float32), pcm[int(end * SR):]])
            words[e] = [int(round(start * 100)) + w for w in segw]
            for k in list(ent):
                if ent[k] > start:
                    ent[k] = round(ent[k] + delta, 2)
            for k in list(words):
                if k != e and ent.get(k, 0) > start:
                    words[k] = [w + int(round(delta * 100)) for w in words[k]]
            report["patched"].append({"part": name, "entry": e, "old_s": round(end - start, 2),
                                      "new_s": round(len(new) / SR, 2), "words": len(segw)})
        encode(pcm, os.path.join(out, name + ".mp3"))
        json.dump({"entries": {str(k): v for k, v in sorted(ent.items())},
                   "words": {str(k): v for k, v in sorted(words.items())}},
                  open(os.path.join(out, name + ".timing.json"), "w"), separators=(",", ":"))
    json.dump(report, open(os.path.join(out, work + ".patch-report.json"), "w"), indent=1)
    print(json.dumps(report)[:3000])


def quiet_point(pcm, a, b):
    """the quietest 10 ms between a and b (seconds): the cut inside the pause between two sentences"""
    hop = 240; db = frames_db(pcm)
    i0, i1 = max(0, int(a * SR / hop)), max(int(a * SR / hop) + 1, int(b * SR / hop))
    seg = db[i0:i1]
    return (i0 + int(np.argmin(seg))) * hop / SR if len(seg) else b


def main_head(pwork, lines_dir, pub, out):
    """Sentence patch: scripts/<work>_patch.json holds, per paragraph, its new opening sentence ("text"), how many
    words that opening had before ("old_words") and whether it is the whole paragraph ("whole"). Only the opening is
    replaced: from the paragraph's start to the pause before its next sentence (the quietest point there)."""
    pp = work_parts(pwork)[0]["lines"]
    work = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", pwork + ".json")))["patch_of"]
    heads = {l["entry"]: l for l in pp if l["entry"] is not None}
    rng, report = np.random.default_rng(13), {"work": work, "patched": []}
    for pi, p in enumerate(work_parts(work)):
        name = f"{work}-p{pi + 1}"
        mine = sorted({l["entry"] for l in p["lines"] if l["entry"] in heads})
        if not mine:
            continue
        pcm = decode(os.path.join(pub, name + ".mp3"))
        tm = json.load(open(os.path.join(pub, name + ".timing.json")))
        ent = {int(k): v for k, v in tm["entries"].items()}
        words = {int(k): v for k, v in tm["words"].items()}
        floor = np.percentile(frames_db(pcm), 10) + 10
        for e in sorted(mine, reverse=True):
            h = heads[e]; W = words.get(e, [])
            if e not in ent or not W:
                print("no timing for entry", e); continue
            start = ent[e]
            a, cut = trim(read_wav(os.path.join(lines_dir, h["id"] + ".wav")))
            a = level(a); a = a + room_tone(len(a), rng)
            meta = json.load(open(os.path.join(lines_dir, h["id"] + ".json")))
            ws = [int(round(max(0.0, s - cut / SR) * 100)) for s in meta["words"]]
            ws = [ws[0] if ws else 0] * h.get("skip", 0) + ws
            if h.get("whole") or h["old_words"] >= len(W):
                later = sorted(v for k, v in ent.items() if v > start)
                limit = later[0] if later else len(pcm) / SR - 1.0
                end = speech_end(pcm, max(start, W[-1] / 100) + 0.05, limit, floor)
                new = chain(a); rest_words = []
            else:
                onset = W[h["old_words"]] / 100
                end = quiet_point(pcm, max(start, onset - 0.45), onset - 0.02)
                pause = max(0.05, 0.30 - (onset - end))
                new = chain(np.concatenate([a, room_tone(int(pause * SR), rng)]))
                rest_words = W[h["old_words"]:]
            old = pcm[int(start * SR): int(end * SR)]
            ro, rn = active_rms(old), active_rms(new)
            if ro and rn:
                new = new * (ro / rn)
            delta = len(new) / SR - (end - start)
            pcm = np.concatenate([pcm[: int(start * SR)], new.astype(np.float32), pcm[int(end * SR):]])
            dc = int(round(delta * 100))
            words[e] = [int(round(start * 100)) + w for w in ws] + [w + dc for w in rest_words]
            for k in list(ent):
                if ent[k] > start:
                    ent[k] = round(ent[k] + delta, 2)
                    if k in words:
                        words[k] = [w + dc for w in words[k]]
            report["patched"].append({"part": name, "entry": e, "old_s": round(end - start, 2),
                                      "new_s": round(len(new) / SR, 2), "words": len(words[e]), "was": len(W)})
        encode(pcm, os.path.join(out, name + ".mp3"))
        json.dump({"entries": {str(k): v for k, v in sorted(ent.items())},
                   "words": {str(k): v for k, v in sorted(words.items())}},
                  open(os.path.join(out, name + ".timing.json"), "w"), separators=(",", ":"))
    json.dump(report, open(os.path.join(out, work + ".patch-report.json"), "w"), indent=1)
    print(json.dumps(report)[:3000])


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0].endswith("_patch"):
        main_head(*a[:4])
    else:
        main(*a)
