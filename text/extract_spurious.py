"""Scripts for Plato's doubtful and spurious works (Lamb, Burges, Jowett translations in Plato Scroll).
Usage: python text/extract_spurious.py BOOKS_DIR MANIFEST.json OUT_DIR
These books carry no speaker codes (every entry is 'N'); the speaker is a label at the start of the text
("Socrates: ...", "Sis.: ..."), which is taken off and turned into the voice. Unlabelled entries go to the
work's narrator (Socrates for the two works he narrates, otherwise the Narrator).
Cleitophon is left out (Horan's version is recorded) and so are the Spanish slots."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import load_book, clean

WORKS = ["hipparch", "rivals", "theages", "sisyph", "axioch", "demod", "eryx", "onjust", "onvirt", "defns"]
ABBR = {"Soc": "Socrates", "Sis": "Sisyphus", "Clin": "Clinias", "Axio": "Axiochus"}
NARR = {"rivals": "Socrates", "eryx": "Socrates", "axioch": "Socrates"}
CREDIT = {"W.R.M. Lamb": "translated by W. R. M. Lamb", "George Burges": "translated by George Burges",
          "Benjamin Jowett": "translated by Benjamin Jowett"}
LABEL = re.compile(r"^([A-Z][A-Za-z]{1,16})\.?:\s+")


def main(books, manifest, out):
    m = {b["meta"]["key"]: b for b in json.load(open(manifest, encoding="utf-8"))["books"]}
    index = []
    for key in WORKS:
        tx = m[key].get("text", {})
        title = m[key]["meta"]["en"]
        entries = load_book(os.path.join(books, f"{key}.js"))[1]
        lines = []
        for i, e in enumerate(entries):
            text = clean(e.get("t", ""))
            if not text:
                continue
            if e.get("sp") in ("HDR", "EH") or (key == "rivals" and i <= 1):   # title page / 'SOCRATES' cast line
                continue
            skip = 0
            mm = LABEL.match(text)
            if mm and (mm.group(1) in ABBR or mm.group(1)[0].isupper()) and len(mm.group(1)) > 1:
                who = ABBR.get(mm.group(1), mm.group(1))
                skip = len(mm.group(0).split())   # the label is shown in the reader but not read
                text = text[mm.end():].strip()
                kind = "speech"
            elif re.match(r"^\((Sis|Soc)\.\s*(.*?)\)\.?$", text):            # "(Sis. Nothing else)."
                mq = re.match(r"^\((Sis|Soc)\.\s*(.*?)\)\.?$", text)
                who, text, kind, skip = ABBR[mq.group(1)], mq.group(2).rstrip(".") + ".", "speech", 1
            elif key not in NARR and lines and lines[-1]["kind"] == "speech":  # a speech running on over entries
                who, kind = lines[-1]["who"], "speech"
            else:
                who, kind = NARR.get(key, "Narrator"), "narration"
            if text:
                lines.append(dict({"entry": i, "who": who, "text": text, "kind": kind}, **({"skip": skip} if skip else {})))
        tr = tx.get("translator", "")
        doc = {"key": key, "title": title, "author": "Plato", "translator": tr,
               "credit": CREDIT.get(tr, f"translated by {tr}"), "parts": [{"name": title, "lines": lines}]}
        json.dump(doc, open(os.path.join(out, f"{key}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        index.append({"key": key, "title": title, "parts": 1, "chars": sum(len(l["text"]) for l in lines),
                      "speakers": sorted({l["who"] for l in lines})})
    json.dump(index, open(os.path.join(out, "index-spurious.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for x in index:
        print(x["key"], x["chars"], x["speakers"])
    print(len(index), "works", sum(x["chars"] for x in index), "chars")


if __name__ == "__main__":
    main(*sys.argv[1:])
