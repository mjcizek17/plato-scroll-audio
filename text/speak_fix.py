"""Spoken-text fixes that keep the word count (the read-along matches words one for one):
- an all-capitals opening (the small capitals printed at the start of a section, "IT IS, I think, ...") and any
  run of two or more all-capital ordinary words are read as ordinary words, not spelled out letter by letter;
- "MSS." is read as "manuscripts".
Letter labels in geometry ("AB", "ABG") are single tokens without lower-case neighbours of their own kind, so they are
left alone unless they open the line in a run with other capitals (works listed in GEOMETRY are never touched).
Usage: python text/speak_fix.py SCRIPT.json..."""
import json, re, sys

GEOMETRY = {"physics", "prior-analytics", "posterior-analytics", "meteorology", "on-the-heavens", "metaphysics",
            "on-memory-and-reminiscence", "nicomachean-ethics", "the-history-of-animals", "euclid-elements", "euclid-data"}
ROMAN = re.compile(r"^[IVXLCDM]+$")
CAPW = re.compile(r"^([“‘(\"']*)([A-Z][A-Z’']+)([.,;:!?’”)\"']*)$")


def word_ok(w):
    return len(w) >= 2 and not ROMAN.match(w) and re.search(r"[AEIOUY]", w)


def fix(text):
    toks = text.split(" ")
    caps = [bool((m := CAPW.match(t)) and word_ok(m.group(2))) for t in toks]
    out = list(toks)
    for i, t in enumerate(toks):
        lead = all(caps[:i + 1])                                       # part of the opening run of capitals
        run = caps[i] and ((i > 0 and caps[i - 1]) or (i + 1 < len(toks) and caps[i + 1]))
        if caps[i] and (lead or run):
            m = CAPW.match(t); w = m.group(2).lower()
            if i == 0 or toks[i - 1].endswith((".", "!", "?", ":", "”")) or (lead and i == 0):
                w = w[0].upper() + w[1:]
            if w.lower() in ("i",):
                w = "I"
            out[i] = m.group(1) + w + m.group(3)
    s = " ".join(out)
    s = re.sub(r"\bMSS\.(?=\s+[a-z])", "manuscripts", s)       # mid-sentence: no full stop to read
    return re.sub(r"\bMSS\.", "manuscripts.", s)


if __name__ == "__main__":
    for f in sys.argv[1:]:
        d = json.load(open(f, encoding="utf-8")); n = 0
        if d.get("key") in GEOMETRY:
            print(f, "skipped (geometry labels)"); continue
        for p in d["parts"]:
            for l in p["lines"]:
                if l["kind"] == "heading":
                    continue
                new = fix(l["text"])
                if new != l["text"]:
                    assert len(new.split()) == len(l["text"].split()), (l["text"], new)
                    l["text"] = new; n += 1
        json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        print(f, n, "lines changed")
