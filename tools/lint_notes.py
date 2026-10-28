"""List the editor's notes the recording will skip (text/notes.py), brackets that look like notes but are read, and
the paragraphs whose figures are written out in words (text/figures.py).
Usage: python tools/lint_notes.py render/queue.json | WORK...
Runs in the produce workflow before rendering; it never fails the run, it only reports, so a new kind of note can be
added to text/notes.py before the recording is made."""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "text"))
import notes as N  # noqa: E402

LOOKS = re.compile(r"\b(?:MSS?|reading|allusion|compare|cp\.|cf\.|translat\w*|fragm\w*|proverb|Greek|corrupt|Il\.|Od\.|"
                   r"Rep\.|Arist\.|see|vide|lit\.|Schol\w*)\b|\b[A-Z][a-z]{1,6}\.\s*[\dIVXivx]", re.I)


def works(args):
    if len(args) == 1 and args[0].endswith(".json"):
        q = json.load(open(args[0]))
        return list(q.get("works", [])) + list((q.get("patch") or {}).keys())
    return args


def main(args):
    total = 0
    for w in works(args):
        p = os.path.join(ROOT, "scripts", re.sub(r"_patch$", "", w) + ".json")
        if not os.path.exists(p):
            continue
        d = json.load(open(p, encoding="utf-8"))
        skipped, read, figures = [], [], []
        for part in d.get("parts", []):
            for l in part.get("lines", []):
                sp, counts = N.plan(l["text"], w)
                if any(c > 1 for c in counts):
                    figures.append((l["entry"], sp[:110]))
                caught = {(a, b) for a, b, _ in N.notes(l["text"], w)}
                for m in N.PAREN.finditer(l["text"]):
                    t = m.group(0)
                    if (m.start(), m.end()) in caught:
                        skipped.append((l["entry"], t))
                    elif LOOKS.search(t) and len(t) < 160:
                        read.append((l["entry"], t))
        total += len(skipped)
        if skipped or read or figures:
            print(f"== {w}: {len(skipped)} notes skipped, {len(read)} brackets read that may be notes, {len(figures)} paragraphs with figures written out")
            for e, t in figures[:12]:
                print(f"   figs  {e}: {t}")
            for e, t in skipped[:200]:
                print(f"   skip  {e}: {t[:110]}")
            for e, t in read[:60]:
                print(f"   READ? {e}: {t[:110]}")
    print(f"{total} notes will not be read aloud (rules: text/notes.py)")


if __name__ == "__main__":
    main(sys.argv[1:])
