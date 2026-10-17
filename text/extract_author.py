"""Extract single-reader scripts (treatises, histories) for one author's English translations.
Usage: python text/extract_author.py BOOKS_DIR MANIFEST.json OUT_DIR AUTHOR READER
Every English work by AUTHOR (Greek-text slots skipped) becomes OUT_DIR/<key>.json with one part per book
heading; every paragraph is read by READER (a cast name). Writes OUT_DIR/index-<author>.json."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import clean, load_book  # noqa: E402


def main(books, manifest, out, author, reader):
    m = json.load(open(manifest, encoding="utf-8"))
    index = []
    for b in m["books"]:
        meta, tx = b["meta"], b.get("text", {})
        tr = (tx.get("translator") or "").strip()
        if meta.get("author") != author or not tr or tr.lower().startswith("greek"):
            continue
        key = meta["key"]
        p = os.path.join(books, f"{key}.js")
        if not os.path.exists(p):
            print("missing", key); continue
        parts, cur = [], None
        for i, e in enumerate(load_book(p)[1]):
            text = clean(e.get("t", ""))
            if not text:
                continue
            if e.get("sp") == "HDR":
                cur = {"name": text, "lines": []}; parts.append(cur)
                cur["lines"].append({"entry": i, "who": reader, "text": text, "kind": "heading"})
                continue
            if cur is None:
                cur = {"name": tx.get("title", key), "lines": []}; parts.append(cur)
            cur["lines"].append({"entry": i, "who": reader, "text": text, "kind": "narration"})
        if len(parts) > 1 and all(len(p["lines"]) <= 1 for p in parts[:1]):
            pass
        tr_clean = re.sub(r"\s*\(\d{4}\)\s*$", "", tr)
        doc = {"key": key, "title": tx.get("title", meta.get("en", key)), "author": author, "translator": tr_clean,
               "parts": parts}
        json.dump(doc, open(os.path.join(out, f"{key}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        index.append({"key": key, "title": doc["title"], "parts": len(parts),
                      "chars": sum(len(l["text"]) for p in parts for l in p["lines"]), "speakers": [reader]})
    json.dump(index, open(os.path.join(out, f"index-{author.lower()}.json"), "w"), ensure_ascii=False, indent=1)
    print(len(index), "works", sum(x["chars"] for x in index), "chars")


if __name__ == "__main__":
    main(*sys.argv[1:])
