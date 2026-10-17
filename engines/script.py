"""Shared: the ordered line list of a work (with its spoken opening), shard planning, word timing helpers."""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NUMS = {"I": "One", "II": "Two", "III": "Three", "IV": "Four", "V": "Five", "VI": "Six", "VII": "Seven",
        "VIII": "Eight", "IX": "Nine", "X": "Ten", "XI": "Eleven", "XII": "Twelve"}


def spoken(title):
    return re.sub(r"\b(XII|XI|X|IX|VIII|VII|VI|IV|V|III|II|I)\b", lambda m: NUMS[m.group(1).upper()], title, flags=re.I)


def load_cast():
    c = json.load(open(os.path.join(ROOT, "cast", "cast.json"), encoding="utf-8"))
    return c


def work_parts(key):
    """[{name, lines:[{id, entry, who, text, kind}]}] with the opening line first in each part."""
    s = json.load(open(os.path.join(ROOT, "scripts", f"{key}.json"), encoding="utf-8"))
    title, parts, n = spoken(s["title"]), [], len(s["parts"])
    for pi, p in enumerate(s["parts"]):
        lines = [dict(l) for l in p["lines"]]
        if n == 1:
            opening = f"Plato's {title}, translated by David Horan."
        else:
            book = spoken(p["name"])
            opening = f"Plato's {title}, translated by David Horan. {book}." if pi == 0 else f"Plato's {title}. {book}."
            if lines and lines[0]["kind"] == "heading":
                lines = lines[1:]
        lines.insert(0, {"entry": None, "who": "Narrator", "text": opening, "kind": "heading"})
        for li, l in enumerate(lines):
            l["id"] = f"p{pi + 1}l{li:04d}"
        parts.append({"name": p["name"], "lines": lines})
    return parts


def engine_of(who, cast):
    c = cast["characters"].get(who)
    return (c or cast["characters"]["Narrator"])["engine"], c is not None


def plan_shards(keys, budget_s=5400):
    """Split works into shards whose estimated render time fits one runner job.
    Estimates: Chatterbox ~0.57 s per character, Kokoro ~0.045 s per character (4-core runner)."""
    cast, shards = load_cast(), []
    for key in keys:
        flat = [l for p in work_parts(key) for l in p["lines"]]
        a, cost, n = 0, 0.0, 0
        for i, l in enumerate(flat):
            eng, _ = engine_of(l["who"], cast)
            c = len(l["text"]) * (0.57 if eng == "chatterbox" else 0.045)
            if cost + c > budget_s and i > a:
                shards.append({"work": key, "shard": n, "a": a, "b": i}); n += 1; a, cost = i, 0.0
            cost += c
        shards.append({"work": key, "shard": n, "a": a, "b": len(flat)})
    return shards


def norm(s):
    return re.sub(r"[^0-9a-z]", "", s.lower())


def word_starts(text, toks):
    """Start time of each whitespace word of `text` from [(token_text, start_or_None)], matched on
    letters/digits so punctuation never shifts alignment; gaps interpolated. Returns (starts, n_interpolated)."""
    words = text.split()
    owner = []
    for wi, w in enumerate(words):
        owner += [wi] * len(norm(w))
    starts, pos = [None] * len(words), 0
    for tt, ts in toks:
        n = norm(tt)
        if not n:
            continue
        if pos < len(owner) and ts is not None and starts[owner[pos]] is None:
            starts[owner[pos]] = ts
        pos += len(n)
    return fill(starts)


def fill(starts):
    known = [i for i, s in enumerate(starts) if s is not None]
    miss = 0
    for i in range(len(starts)):
        if starts[i] is None:
            miss += 1
            prev = max([k for k in known if k < i], default=None)
            nxt = min([k for k in known if k > i], default=None)
            if prev is not None and nxt is not None:
                starts[i] = starts[prev] + (starts[nxt] - starts[prev]) * (i - prev) / (nxt - prev)
            else:
                starts[i] = starts[prev] if prev is not None else (starts[nxt] if nxt is not None else 0.0)
    for i in range(1, len(starts)):
        starts[i] = max(starts[i], starts[i - 1])
    return starts, miss


if __name__ == "__main__":
    import sys
    q = json.load(open(sys.argv[1]))
    print(json.dumps(plan_shards(q["works"]), separators=(",", ":")))
