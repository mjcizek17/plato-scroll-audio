"""Scripts for Plato in Benjamin Jowett's translation (the "-b" slots in Plato Scroll), same cast as Horan's.
Usage: python text/extract_jowett.py BOOKS_DIR MANIFEST.json OUT_DIR
Jowett's books carry no speaker codes: every entry is 'N' and the speaker is an inline label
(<span class="speaker-label">Socrates:</span>), which is taken off and turned into the voice; the label's word is
shown in the reader but not read ("skip"). Unlabelled entries continue the previous speaker in a dramatic dialogue
and go to the narrating character in a narrated one (Socrates in Republic, Charmides, Protagoras, Euthydemus,
Lysis and the Apology; Phaedo in Phaedo; Apollodorus in Symposium; Cephalus in Parmenides). The narrator reads the
quoted speeches too. Republic and Laws are one part per book; Jowett's marginal cast lines in the Republic
("Socrates - Glaucon") are not read. Writes OUT_DIR/<key>.json and OUT_DIR/index-jowett.json."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import load_book, clean  # noqa: E402

NARR = {"rep-b": "Socrates", "chrm-b": "Socrates", "prot-b": "Socrates", "euthy-b": "Socrates", "lysis-b": "Socrates",
        "apol-b": "Socrates", "phae-b": "Phaedo", "symp-b": "Apollodorus", "parm-b": "Cephalus"}
# Jowett's names -> the cast's (Horan's) names
ALIAS = {"Athenian": "Athenian Stranger", "Cleinias": "Clinias", "Euclid": "Euclides", "Boy": "Servant", "Son": "Aristides"}
# true speakers; anything else labelled is a word of the text ("Impossible:", "True.", "Again:")
SPEAKERS = {"Socrates", "Euthyphro", "Crito", "Hippias", "Eudicus", "Alcibiades", "Lysimachus", "Nicias", "Laches", "Melesias",
            "Son", "Ion", "Echecrates", "Phaedo", "Hermogenes", "Cratylus", "Companion", "Callicles", "Chaerephon", "Gorgias",
            "Polus", "Meno", "Boy", "Anytus", "Menexenus", "Apollodorus", "Phaedrus", "Euclid", "Terpsion", "Theodorus",
            "Theaetetus", "Timaeus", "Hermocrates", "Critias", "Stranger", "Young Socrates", "Protarchus", "Philebus",
            "Athenian", "Cleinias", "Megillus"}
LABEL = re.compile(r'^\s*<span class="speaker-label">([^<]*?):?</span>\s*')
CAST_LINE = re.compile(r"^[A-Z][a-z]+( - [A-Z][a-z]+)+$")   # Republic: "Socrates - Glaucon"


def main(books, manifest, out):
    os.makedirs(out, exist_ok=True)
    m = json.load(open(manifest, encoding="utf-8"))
    index = []
    for b in m["books"]:
        meta, tx = b["meta"], b.get("text", {})
        key = meta["key"]
        if not key.endswith("-b") or meta.get("author") != "Plato" or tx.get("translator") != "Benjamin Jowett":
            continue
        title = tx.get("title") or meta["en"]
        entries = load_book(os.path.join(books, f"{key}.js"))[1]
        narr = NARR.get(key)
        parts, cur, last = [], None, None
        for i, e in enumerate(entries):
            raw = e.get("t", "")
            if e.get("sp") == "HDR":
                name = re.sub(r"\b([ivxlc]+)\b", lambda mm: mm.group(1).upper(), clean(raw).rstrip(".").title(), flags=re.I)
                if not re.match(r"^Book\b", name):   # a title line ("ALCIBIADES I"), not a book division
                    continue
                cur = {"name": name, "lines": []}; parts.append(cur)
                cur["lines"].append({"entry": i, "who": "Narrator", "text": name, "kind": "heading"})
                continue
            if e.get("sp") in ("EH", "IMG"):
                continue
            if cur is None:
                cur = {"name": title, "lines": []}; parts.append(cur)
            mm = LABEL.match(raw)
            skip = 0
            if mm and mm.group(1) in SPEAKERS:
                who = ALIAS.get(mm.group(1), mm.group(1))
                text = clean(raw[mm.end():])
                skip = len(clean(mm.group(0)).split()) or 1
                kind = "speech"; last = who
            else:
                text = clean(raw)
                if not text or (key == "rep-b" and CAST_LINE.match(text)):
                    continue
                if narr:
                    who, kind = narr, "narration"
                elif last:
                    who, kind = last, "speech"
                else:
                    who, kind = "Narrator", "narration"
            if not text:
                continue
            line = {"entry": i, "who": who, "text": text, "kind": kind}
            if skip:
                line["skip"] = skip
            cur["lines"].append(line)
        doc = {"key": key, "title": title, "author": "Plato", "translator": "Benjamin Jowett",
               "credit": "translated by Benjamin Jowett", "parts": parts}
        json.dump(doc, open(os.path.join(out, f"{key}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        chars = sum(len(l["text"]) for p in parts for l in p["lines"])
        index.append({"key": key, "title": title, "parts": len(parts), "chars": chars,
                      "speakers": sorted({l["who"] for p in parts for l in p["lines"]})})
        print(key, len(parts), "parts", chars, index[-1]["speakers"])
    json.dump(index, open(os.path.join(out, "index-jowett.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(index), "works", sum(x["chars"] for x in index), "chars")


if __name__ == "__main__":
    main(*sys.argv[1:])
