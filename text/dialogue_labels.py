"""Give labelled speeches in a single-reader script their own voices: a line opening with a speaker label
("Tat: ...", "[Hermes:] ...") is read by that character and the label itself is not read (its words take the first
spoken word's timing: "skip"). Usage: python text/dialogue_labels.py SCRIPT.json NAME=Cast NAME=Cast ...
e.g. Hermes="Hermes Reader" Tat=Tat Mind=Mind"""
import json, re, sys

if __name__ == "__main__":
    f, pairs = sys.argv[1], dict(a.split("=", 1) for a in sys.argv[2:])
    d = json.load(open(f, encoding="utf-8")); n = 0
    lab = re.compile(r"^(\[?(" + "|".join(map(re.escape, pairs)) + r")\]?[:.])\s+")
    for p in d["parts"]:
        for l in p["lines"]:
            if l["kind"] == "heading":
                continue
            m = lab.match(l["text"])
            if m:
                l["who"] = pairs[m.group(2)]; l["skip"] = len(m.group(1).split())
                l["text"] = l["text"][m.end():]; l["kind"] = "speech"; n += 1
    json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f, n, "labelled speeches")
