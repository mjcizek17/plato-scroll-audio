"""Extract single-reader scripts (treatises, histories) for one author's English translations.
Usage: python text/extract_author.py BOOKS_DIR MANIFEST.json OUT_DIR AUTHOR READER [MIN_PART_CHARS]
MIN_PART_CHARS (e.g. 22000, about 25 minutes): consecutive short chapters are joined into one part (one MP3) until it
reaches that length; the joined chapters keep their headings, read in place.
Every English work by AUTHOR (Greek-text slots skipped) becomes OUT_DIR/<key>.json with one part per book
heading; every paragraph is read by READER (a cast name). Writes OUT_DIR/index-<author>.json."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import clean, load_book  # noqa: E402


def heading(t):
    """'CHAP. IV.' -> 'Chapter IV', 'INTRODUCTION.' -> 'Introduction' (same number of words, so the read-along
    still matches the heading on the page)"""
    t = re.sub(r"\bCHAP\.\s*", "CHAPTER ", t.strip()) if re.match(r"^CHAP\.", t.strip()) else t.strip()
    t = re.sub(r"^Chap\.\s*", "Chapter ", t)
    if t.upper() == t and re.search(r"[A-Z]{3}", t):
        t = re.sub(r"\b([ivxlc]+)\b", lambda m: m.group(1).upper(), t.title(), flags=re.I)
    return t.rstrip(".")


CREDIT = {"After Evelyn-White (Loeb)": "translated after Hugh G. Evelyn-White"}


def merge(parts, min_chars):
    """join consecutive short parts; the first part (often just the title page) joins the next"""
    out = []
    for p in parts:
        n = sum(len(l["text"]) for l in p["lines"])
        if out and out[-1]["_n"] < min_chars:
            out[-1]["lines"] += p["lines"]; out[-1]["_n"] += n
            if out[-1]["_n0"] < 400: out[-1]["name"] = p["name"]; out[-1]["_n0"] = 10 ** 9   # a title page names nothing
        else:
            out.append({"name": p["name"], "lines": list(p["lines"]), "_n": n, "_n0": n})
    if len(out) > 1 and out[-1]["_n"] < min_chars / 3:          # a short tail joins the part before
        out[-2]["lines"] += out[-1]["lines"]; out.pop()
    for p in out:
        p.pop("_n"); p.pop("_n0")
        if p["lines"] and p["lines"][0]["kind"] != "heading":   # the part's name is announced: make it its first line
            p["lines"].insert(0, {"entry": p["lines"][0]["entry"], "who": p["lines"][0]["who"], "text": p["name"], "kind": "heading"})
    return out


def main(books, manifest, out, author, reader, min_chars="0"):
    min_chars = int(min_chars)
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
        parts, cur, section = [], None, None
        for i, e in enumerate(load_book(p)[1]):
            if e.get("sp") == "IMG":            # picture captions are shown, not read
                continue
            text = clean(e.get("t", ""))
            if not text:
                continue
            if e.get("sp") == "HDR" and len(re.findall(r"\d", text)) > 0.3 * len(re.sub(r"\s", "", text)):
                continue                        # a number table set as a heading (Theoretic Arithmetic): shown, not read
            if e.get("sp") == "HDR":
                text = heading(text)
                if re.match(r"^Section\b", text, re.I): section = text
                name = f"{section}, {text}" if section and re.match(r"^Chapter\b", text) else text   # Mysteries: chapters restart per Section
                cur = {"name": name, "lines": []}; parts.append(cur)
                cur["lines"].append({"entry": i, "who": reader, "text": text, "kind": "heading"})
                continue
            if cur is None:
                cur = {"name": tx.get("title", key), "lines": []}; parts.append(cur)
            cur["lines"].append({"entry": i, "who": reader, "text": text, "kind": "narration"})
        if len(parts) > 1 and all(len(p["lines"]) <= 1 for p in parts[:1]):
            pass
        if len(parts) > 1 and sum(len(l["text"]) for l in parts[0]["lines"]) < 400:   # a title page joins the first chapter
            parts[1]["lines"] = [l for l in parts[0]["lines"] if l["kind"] != "heading"] + parts[1]["lines"]; parts.pop(0)
        if min_chars and len(parts) > 1:
            parts = merge(parts, min_chars)
        tr_clean = re.sub(r"\s*\(\d{4}\)\s*$", "", tr)
        doc = {"key": key, "title": tx.get("title", meta.get("en", key)), "author": author, "translator": tr_clean,
               "parts": parts}
        if tr_clean in CREDIT: doc["credit"] = CREDIT[tr_clean]
        json.dump(doc, open(os.path.join(out, f"{key}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        index.append({"key": key, "title": doc["title"], "parts": len(parts),
                      "chars": sum(len(l["text"]) for p in parts for l in p["lines"]), "speakers": [reader]})
    json.dump(index, open(os.path.join(out, f"index-{author.lower()}.json"), "w"), ensure_ascii=False, indent=1)
    print(len(index), "works", sum(x["chars"] for x in index), "chars")


if __name__ == "__main__":
    main(*sys.argv[1:])
