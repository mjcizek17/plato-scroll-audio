"""The gate before any rendering: everything in the queue must be safe to read aloud, or the run stops here.
Usage: python tools/speech_gate.py render/queue.json
Fails (exit 1) when:
  - a line's spoken words cannot be mapped back to its printed words (text/notes.py would fall back to reading it
    as printed, figures and all);
  - a figure is still left to the voice in a work other than the geometry works (text/speak_fix.GEOMETRY);
  - a speaker in a queued work would be read by the retired "Narrator" clip (cast/refs/narrator.wav), which the
    user has asked never to be used again — recast the speaker first (title headings announced by it only warn);
  - a speaker is not cast at all.
Prints, for every work, a sample of what changed between page and voice so it can be eyed before the run."""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "text"))
sys.path.insert(0, os.path.join(ROOT, "engines"))
import notes as N  # noqa: E402
import speak_fix  # noqa: E402
from script import load_cast, char_spec, work_parts  # noqa: E402

RETIRED_REFS = {"narrator"}


def queued(path):
    q = json.load(open(path))
    works = list(q.get("works", []))
    patch = q.get("patch") or {}
    return [(re.sub(r"_patch$", "", w), None) for w in works] + [(w, set(e["entry"] if isinstance(e, dict) else e for e in v)) for w, v in patch.items()]


def main(path):
    cast = load_cast()
    bad = 0
    for work, entries in queued(path):
        parts = work_parts(work)
        if not parts:
            print(f"!! {work}: no script"); bad += 1; continue
        mism, figs, changed, speakers, head_only = [], [], [], set(), set()
        for p in parts:
            for l in p["lines"]:
                if entries is not None and l.get("entry") not in entries and str(l.get("entry")) not in {str(e) for e in entries}:
                    continue
                (head_only if l.get("kind") == "heading" else speakers).add(l["who"])
                spoken, counts = N.plan(l["text"], work)
                words = l["text"].split()
                if len(counts) != len(words) or sum(counts) != len(spoken.split()):
                    mism.append((l["id"], l["text"][:90]))
                elif spoken != l["text"]:
                    changed.append((l["id"], spoken[:120]))
                if re.search(r"\d", spoken) and re.sub(r"-b$", "", work) not in speak_fix.GEOMETRY:
                    figs.append((l["id"], spoken[:120]))
        for who in sorted(speakers):
            c = char_spec(cast, work, who)
            if c is cast["characters"]["Narrator"] and who != "Narrator" and not any(
                    k in cast["characters"] for k in (f"{work}:{who}", f"{re.sub(r'-b$', '', work)}:{who}", who)):
                print(f"!! {work}: {who} is not cast"); bad += 1
            if c.get("ref") in RETIRED_REFS:
                print(f"!! {work}: {who} would be read by the retired '{c['ref']}' clip — recast before rendering"); bad += 1
        for who in sorted(head_only - speakers):
            if char_spec(cast, work, who).get("ref") in RETIRED_REFS:
                print(f"   {work}: the title and headings are announced by {who} (retired clip) — allowed, but recast it to change")
        for lid, t in mism:
            print(f"!! {work} {lid}: spoken words cannot be mapped to the page: {t}"); bad += 1
        for lid, t in figs:
            print(f"!! {work} {lid}: a figure is left to the voice: {t}"); bad += 1
        print(f"== {work}: {len(changed)} lines read differently from the page" + (f" ({len(entries)} patched paragraphs)" if entries else ""))
        for lid, t in changed[:8]:
            print(f"   {lid}: {t}")
    print("speech gate:", "FAILED" if bad else "passed", f"({bad} problems)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1])
