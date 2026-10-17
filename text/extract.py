"""Extract speaker-by-speaker scripts of Horan's Plato from Plato Scroll book files.
Usage: python text/extract.py BOOKS_DIR MANIFEST.json OUT_DIR
BOOKS_DIR holds <key>.js as shipped in the app (assets/books/). Writes OUT_DIR/<key>.json:
{key, title, parts: [{name, lines: [{entry, who, text, kind}]}]} where kind is heading|speech|narration.
Republic and Laws are split into one part per book at their HDR entries."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quotes import segments

SPEAKERS = {  # Plato Scroll's global table (core/app.js getSpeakerName)
    "S": "Socrates", "A": "Alcibiades", "M": "Meletus", "L": "Clitophon", "H": "Hermogenes", "C": "Cratylus",
    "T": "Timaeus", "Ci": "Critias", "He": "Hermocrates", "Cr": "Crito", "P": "Plato", "At": "Athenian Stranger",
    "Cl": "Clinias", "Me": "Megillus", "E": "Euthyphro", "Ca": "Callicles", "Ch": "Chaerephon", "Go": "Gorgias",
    "Po": "Polus", "Hi": "Hippias", "Eu": "Eudicus", "Io": "Ion", "Ly": "Lysimachus", "Ni": "Nicias", "La": "Laches",
    "Mel": "Melesias", "Bo": "Boys", "Hp": "Hippothales", "Ct": "Ctesippus", "Ls": "Lysis", "Mx": "Menexenus",
    "Mn": "Meno", "An": "Anytus", "Sv": "Servant", "Co": "Companion", "Z": "Zeno", "Pa": "Parmenides",
    "Ar": "Aristoteles", "Ec": "Echecrates", "Ph": "Phaedo", "Si": "Simmias", "Ce": "Cebes", "Wa": "Warder",
    "Xa": "Xanthippe", "Pn": "Poisoner", "Pd": "Phaedrus", "Pr": "Protarchus", "Pl": "Philebus", "Td": "Theodorus",
    "Tt": "Theaetetus", "St": "Stranger", "Ys": "Young Socrates", "Ap": "Apollodorus", "Ad": "Aristodemus",
    "Ps": "Pausanias", "Er": "Eryximachus", "Ah": "Aristophanes", "Ag": "Agathon", "Di": "Diotima",
    "Ek": "Euclides", "Tp": "Terpsion",
}
# Who reads narration ('N') in each narrated work (standing decision).
NARRATOR = {"rep": "Socrates", "chrm": "Socrates", "prot": "Socrates", "euthy": "Socrates", "lysis": "Socrates",
            "phae": "Phaedo", "symp": "Apollodorus", "parm": "Cephalus", "epist": "Plato"}
HEADINGS = {"HDR", "EH"}
# Speaker of each quotation inside narration, per work: {entry: [speaker per quotation]} (text/attrib/KEY.json)
ATTRIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "attrib")
ATTRIB = {f[:-5]: json.load(open(os.path.join(ATTRIB_DIR, f), encoding="utf-8"))
          for f in (os.listdir(ATTRIB_DIR) if os.path.isdir(ATTRIB_DIR) else []) if f.endswith(".json")}
QUOTE_SPLIT = {"lysis": "Socrates"}
SUP = re.compile(r"[¹²³⁰-⁹]+")


def clean(t):
    t = re.sub(r"<br\s*/?>", " ", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = SUP.sub("", t)                       # footnote markers are not read
    t = re.sub(r"\[[^\]]*\]", "", t)          # editorial brackets
    t = t.replace("\n", ". ") if t.count("\n") else t
    return re.sub(r"\s+", " ", t).strip()


def load_book(path):
    s = open(path, encoding="utf-8").read()
    i = s.index("__hermes_register_book(") + len("__hermes_register_book(")
    return json.loads("[" + s[i:s.rindex(");})();")] + "]")


def main(books, manifest, out):
    os.makedirs(out, exist_ok=True)
    m = json.load(open(manifest, encoding="utf-8"))
    index = []
    for b in m["books"]:
        tx = b.get("text", {})
        if tx.get("translator") != "David Horan":
            continue
        key = b["meta"]["key"]
        local = tx.get("speakers") or {}
        entries = load_book(os.path.join(books, f"{key}.js"))[1]
        parts, cur = [], None
        for i, e in enumerate(entries):
            sp, text = e.get("sp"), clean(e.get("t", ""))
            if not text:
                continue
            if sp == "HDR":
                cur = {"name": text.title(), "lines": []}; parts.append(cur)
                cur["lines"].append({"entry": i, "who": "Narrator", "text": text.title(), "kind": "heading"})
                continue
            if cur is None:
                cur = {"name": tx.get("title", key), "lines": []}; parts.append(cur)
            if sp in HEADINGS:
                who, kind = "Narrator", "heading"
            elif sp == "N":
                who, kind = NARRATOR.get(key, "Narrator"), "narration"
            else:
                who, kind = local.get(sp) or SPEAKERS.get(sp, sp), "speech"
            if key in ATTRIB and kind == "narration":
                labels, q = ATTRIB[key].get(str(i), []), 0
                for k2, seg in segments(text):
                    if k2 == "quote" and q < len(labels):
                        cur["lines"].append({"entry": i, "who": labels[q], "text": seg, "kind": "speech"}); q += 1
                    else:
                        cur["lines"].append({"entry": i, "who": who, "text": seg, "kind": "narration"})
            elif key in QUOTE_SPLIT and kind == "speech":
                # Narrated works laid out by speaker (Lysis): tags outside the quotes are the narrator's.
                segs = segments(text)
                if any(k2 == "quote" for k2, _ in segs):
                    for k2, seg in segs:
                        cur["lines"].append({"entry": i, "who": who if k2 == "quote" else QUOTE_SPLIT[key],
                                             "text": seg, "kind": "speech" if k2 == "quote" else "narration"})
                else:
                    cur["lines"].append({"entry": i, "who": who, "text": text, "kind": kind})
            else:
                cur["lines"].append({"entry": i, "who": who, "text": text, "kind": kind})
        for p in parts:  # one take for consecutive pieces of one entry by the same voice
            merged = []
            for l in p["lines"]:
                if merged and merged[-1]["entry"] == l["entry"] and merged[-1]["who"] == l["who"] and l["kind"] != "heading":
                    merged[-1]["text"] += " " + l["text"]
                else:
                    merged.append(l)
            p["lines"] = merged
        doc = {"key": key, "title": tx.get("title", key), "parts": parts}
        json.dump(doc, open(os.path.join(out, f"{key}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        chars = sum(len(l["text"]) for p in parts for l in p["lines"])
        index.append({"key": key, "title": doc["title"], "parts": len(parts), "chars": chars,
                      "speakers": sorted({l["who"] for p in parts for l in p["lines"]})})
    json.dump(index, open(os.path.join(out, "index.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(index), "works", sum(x["chars"] for x in index), "chars")


if __name__ == "__main__":
    main(*sys.argv[1:])
