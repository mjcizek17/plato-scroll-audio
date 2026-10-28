"""Cut the editor's notes out of a published recording: "(Compare Symp.)", "(Il.)", "(Greek)", "(Or, reading ...)" and
the rest of what text/notes.py lists, read aloud before the recording tools learned to skip them.
Usage: python tools/slice_notes.py WORK PUBDIR OUTDIR [--dry]
  PUBDIR  the published WORK-pN.mp3 and WORK-pN.timing.json
For each note: the audio from just before its first word (the quietest point in the 0.25 s before it) to the end of its
speech (the first 0.2 s of silence after its last word, or the next spoken word, whichever comes first) is removed,
with a 10 ms crossfade. The pause that came before the note stays, so the sentence runs on as it would have been read.
Read-along timing: the note's words stay in the list (the page still prints them) with the time of the cut, so the
highlight passes straight over them; every later time moves back by the length cut.
Writes OUTDIR/WORK-pN.mp3 + .timing.json for each changed part and OUTDIR/WORK.slice-report.json."""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from patch import decode, encode, frames_db, speech_end, SR  # noqa: E402
from script import work_parts  # noqa: E402  (patch.py puts engines/ on the path)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "text"))
import notes as N  # noqa: E402
import numpy as np  # noqa: E402


def quiet_point(db, a, b):
    hop = 240
    i0, i1 = max(0, int(a * SR / hop)), max(int(a * SR / hop) + 1, int(b * SR / hop))
    seg = db[i0:i1]
    return (i0 + int(np.argmin(seg))) * hop / SR if len(seg) else a


def runs(mask):
    i = 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j + 1 < len(mask) and mask[j + 1]:
                j += 1
            yield i, j
            i = j + 1
        else:
            i += 1


def plan_part(work, p, tm):
    """[(entry, first_word_index, last_word_index, next_spoken_index or None, text)] for one part"""
    words = {int(k): v for k, v in tm["words"].items()}
    by_entry, out, bad = {}, [], []
    for l in p["lines"]:
        if l["entry"] is not None:
            by_entry.setdefault(l["entry"], []).append(l)
    for e, lines in by_entry.items():
        W = words.get(e)
        flat = []                                      # one flag per timing word: silent?
        for l in lines:
            flat += [False] * l.get("skip", 0) + N.silent_mask(l["text"], work)
        if not any(flat):
            continue
        if W is None or len(W) != len(flat):
            bad.append({"entry": e, "timing_words": None if W is None else len(W), "text_words": len(flat)})
            continue
        txt = [w for l in lines for w in ["·"] * l.get("skip", 0) + l["text"].split()]
        for i, j in runs(flat):
            nxt = next((k for k in range(j + 1, len(flat)) if not flat[k]), None)
            out.append((e, i, j, nxt, " ".join(txt[i: j + 1])))
    return out, bad


def main(work, pub, outdir, dry=False):
    os.makedirs(outdir, exist_ok=True)
    report = {"work": work, "cuts": [], "skipped": []}
    for pi, p in enumerate(work_parts(work)):
        name = f"{work}-p{pi + 1}"
        tp = os.path.join(pub, name + ".timing.json")
        if not os.path.exists(tp):
            continue
        tm = json.load(open(tp))
        cuts, bad = plan_part(work, p, tm)
        report["skipped"] += [dict(b, part=name) for b in bad]
        if not cuts:
            continue
        ent = {int(k): v for k, v in tm["entries"].items()}
        words = {int(k): list(v) for k, v in tm["words"].items()}
        if dry:
            report["cuts"] += [{"part": name, "entry": e, "words": [i, j], "text": t} for e, i, j, n, t in cuts]
            continue
        pcm = decode(os.path.join(pub, name + ".mp3"))
        db = frames_db(pcm)
        floor = np.percentile(db, 10) + 10
        total = len(pcm) / SR
        # work from the end, so the times of the cuts still to come stay valid
        for e, i, j, nxt, text in sorted(cuts, key=lambda c: words[c[0]][c[1]], reverse=True):
            W = words[e]
            # a note cut in an earlier pass: its words all sit at the time of the cut, as does the word after it
            if (j > i and W[j] == W[i]) or (nxt is not None and W[nxt] == W[j]) or (i > 0 and W[i] == W[i - 1]):
                report["skipped"].append({"part": name, "entry": e, "words": [i, j], "text": text, "why": "already cut"})
                continue
            t_first, t_last = W[i] / 100, W[j] / 100
            prev = W[i - 1] / 100 if i > 0 else ent.get(e, t_first)
            if nxt is not None:
                limit = W[nxt] / 100
            else:
                later = sorted(v for v in ent.values() if v > t_first)
                limit = later[0] if later else total - 0.3
            t0 = quiet_point(db, max(prev + 0.05, t_first - 0.25), t_first + 0.03)
            t1 = speech_end(pcm, t_last + 0.05, limit, floor)
            if nxt is not None and limit - t1 <= 0.8:
                # only a pause between the note and the next word: it goes too (the pause before the note stays)
                t1 = quiet_point(db, max(t1, limit - 0.12), limit + 0.01)
            if t1 - t0 < 0.15 or t1 - t0 > 40:
                report["skipped"].append({"part": name, "entry": e, "words": [i, j], "text": text,
                                          "why": f"cut of {t1 - t0:.2f} s looks wrong"})
                continue
            a, b = int(t0 * SR), int(t1 * SR)
            f = int(0.01 * SR)
            ramp = np.linspace(0, 1, f, dtype=np.float32)
            joint = pcm[a - f: a] * (1 - ramp) + pcm[b - f: b] * ramp if a >= f else pcm[b - f: b]
            pcm = np.concatenate([pcm[: max(0, a - f)], joint.astype(np.float32), pcm[b:]])
            d = (b - a) / SR
            dc = int(round(d * 100)); c0 = int(round(t0 * 100))
            for k in list(ent):
                if ent[k] > t0 + 0.001:
                    ent[k] = round(max(t0, ent[k] - d), 2)
            for k, ws in words.items():
                for x in range(len(ws)):
                    if k == e and i <= x <= j:
                        ws[x] = c0
                    elif ws[x] > c0:
                        ws[x] = max(c0, ws[x] - dc)
            db = frames_db(pcm)
            report["cuts"].append({"part": name, "entry": e, "words": [i, j], "text": text,
                                   "at": round(t0, 2), "cut_s": round(d, 2)})
        encode(pcm, os.path.join(outdir, name + ".mp3"))
        json.dump({"entries": {str(k): v for k, v in sorted(ent.items())},
                   "words": {str(k): v for k, v in sorted(words.items())}},
                  open(os.path.join(outdir, name + ".timing.json"), "w"), separators=(",", ":"))
    json.dump(report, open(os.path.join(outdir, work + ".slice-report.json"), "w"), indent=1, ensure_ascii=False)
    print(work, len(report["cuts"]), "cuts,", len(report["skipped"]), "skipped")
    for s in report["skipped"]:
        print("  skipped", s)


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if x != "--dry"]
    main(a[0], a[1], a[2], dry="--dry" in sys.argv)
