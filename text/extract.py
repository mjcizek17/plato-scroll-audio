"""Extract speaker-by-speaker scripts of Horan's Plato from Plato Scroll book files.
Usage: python text/extract.py BOOKS_DIR MANIFEST.json OUT_DIR
BOOKS_DIR holds <key>.js as shipped in the app (assets/books/). Writes OUT_DIR/<key>.json:
{key, title, parts: [{name, lines: [{entry, who, text, kind}]}]} where kind is heading|speech|narration.
Republic and Laws are split into one part per book at their HDR entries."""
import json, os, re, sys

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
            cur["lines"].append({"entry": i, "who": who, "text": text, "kind": kind})
        doc = {"key": key, "title": tx.get("title", key), "parts": parts}
        json.dump(doc, open(os.path.join(out, f"{key}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        chars = sum(len(l["text"]) for p in parts for l in p["lines"])
        index.append({"key": key, "title": doc["title"], "parts": len(parts), "chars": chars,
                      "speakers": sorted({l["who"] for p in parts for l in p["lines"]})})
    json.dump(index, open(os.path.join(out, "index.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(index), "works", sum(x["chars"] for x in index), "chars")


if __name__ == "__main__":
    main(*sys.argv[1:])
