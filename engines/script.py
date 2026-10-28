"""Shared: the ordered line list of a work (with its spoken opening), shard planning, word timing helpers."""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NUMS = {"I": "One", "II": "Two", "III": "Three", "IV": "Four", "V": "Five", "VI": "Six", "VII": "Seven",
        "VIII": "Eight", "IX": "Nine", "X": "Ten", "XI": "Eleven", "XII": "Twelve", "XIII": "Thirteen", "XIV": "Fourteen"}


def spoken(title):
    return re.sub(r"\b(XIV|XIII|XII|XI|X|IX|VIII|VII|VI|IV|V|III|II|I)\b", lambda m: NUMS[m.group(1).upper()], title, flags=re.I)


def load_cast():
    c = json.load(open(os.path.join(ROOT, "cast", "cast.json"), encoding="utf-8"))
    return c


def work_parts(key):
    """[{name, lines:[{id, entry, who, text, kind}]}] with the opening line first in each part."""
    s = json.load(open(os.path.join(ROOT, "scripts", f"{key}.json"), encoding="utf-8"))
    title, parts, n = spoken(s["title"]), [], len(s["parts"])
    author, tr = s.get("author", "Plato"), s.get("translator", "David Horan")
    credit = s.get("credit") or f"translated by {tr}"
    head = f"Plato's {title}" if author == "Plato" else f"{author}, {title}"
    for pi, p in enumerate(s["parts"]):
        lines = [dict(l) for l in p["lines"]]
        if n == 1:
            opening = f"{head}, {credit}."
            if author != "Plato" and lines and lines[0]["kind"] == "heading":
                lines = lines[1:]  # a lone heading repeats the title
        else:
            book = spoken(p["name"]).rstrip(". ")
            opening = f"{head}, {credit}. {book}." if pi == 0 else f"{head}. {book}."
            if lines and lines[0]["kind"] == "heading":
                lines = lines[1:]
        lines.insert(0, {"entry": None, "who": "Narrator", "text": opening, "kind": "heading"})
        for li, l in enumerate(lines):
            l["id"] = f"p{pi + 1}l{li:04d}"
        parts.append({"name": p["name"], "lines": lines})
    return parts


def char_spec(cast, work, who):
    """The cast entry for a speaker in a work: work-qualified key first (symp:Companion), then the name.
    Unknown speakers fall back to the Narrator (and are listed by tools/check_cast.py)."""
    ch = cast["characters"]
    base = re.sub(r"-b$", "", work)   # Jowett's slots (alc1-b) share Horan's work-qualified cast (alc1)
    c = ch.get(f"{work}:{who}") or ch.get(f"{base}:{who}") or ch.get(who)
    return c or ch["Narrator"]


def engine_of(who, cast, work=""):
    ch = cast["characters"]
    base = re.sub(r"-b$", "", work)
    c = ch.get(f"{work}:{who}") or ch.get(f"{base}:{who}") or ch.get(who)
    return (c or ch["Narrator"])["engine"], c is not None


def plan_shards(keys, budget_s=5400):
    budget_s = float(budget_s)
    """Split works into shards whose estimated render time fits one runner job.
    Estimates: Chatterbox ~0.57 s per character, Kokoro ~0.045 s per character (4-core runner)."""
    cast, shards = load_cast(), []
    for key in keys:
        flat = [l for p in work_parts(key) for l in p["lines"]]
        a, cost, n = 0, 0.0, 0
        for i, l in enumerate(flat):
            eng, _ = engine_of(l["who"], cast, key)
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


def plan_ranges(ranges, budget_s=5400):
    """Re-render only some lines: {work: [[a, b], ...]} (flat line indices, b exclusive), split by budget.
    Shard numbers start at 900 so their artifacts never share a name with the earlier run's."""
    cast, shards = load_cast(), []
    for key, rs in ranges.items():
        flat = [l for p in work_parts(key) for l in p["lines"]]
        n = 900
        for a0, b0 in rs:
            a, cost = a0, 0.0
            for i in range(a0, min(b0, len(flat))):
                eng, _ = engine_of(flat[i]["who"], cast, key)
                c = len(flat[i]["text"]) * (0.57 if eng == "chatterbox" else 0.045)
                if cost + c > float(budget_s) and i > a:
                    shards.append({"work": key, "shard": n, "a": a, "b": i}); n += 1; a, cost = i, 0.0
                cost += c
            shards.append({"work": key, "shard": n, "a": a, "b": min(b0, len(flat))}); n += 1
    return shards


def plan_patch(patch, budget_s=5400):
    """Re-record whole paragraphs: {work: [entry, ...]} -> shards listing the flat indices of their lines ("a" is the
    comma-separated list, "b" is "-"), packed up to the budget. Shard numbers start at 950."""
    cast, shards = load_cast(), []
    for key, ents in patch.items():
        want = set(int(e) for e in ents)
        flat = [l for p in work_parts(key) for l in p["lines"]]
        idx = [i for i, l in enumerate(flat) if l["entry"] in want]
        n, cur, cost = 950, [], 0.0
        for i in idx:
            eng, _ = engine_of(flat[i]["who"], cast, key)
            c = len(flat[i]["text"]) * (0.57 if eng == "chatterbox" else 0.045)
            if cur and cost + c > float(budget_s):
                shards.append({"work": key, "shard": n, "a": ",".join(map(str, cur)) + ",", "b": "-"}); n += 1; cur, cost = [], 0.0
            cur.append(i); cost += c
        if cur:
            shards.append({"work": key, "shard": n, "a": ",".join(map(str, cur)) + ",", "b": "-"})
    return shards


if __name__ == "__main__":
    import sys
    q = json.load(open(sys.argv[1]))
    # ranges: re-render only those lines of those works; any other work in "works" is rendered whole
    if q.get("no_render"):   # assemble only, from the lines of reuse_run (nothing is rendered)
        print("[]"); sys.exit(0)
    if q.get("patch"):
        print(json.dumps(plan_patch(q["patch"], q.get("budget", 5400)), separators=(",", ":"))); sys.exit(0)
    rest = [w for w in q["works"] if w not in q.get("ranges", {})]
    plan = (plan_ranges(q["ranges"], q.get("budget", 5400)) if q.get("ranges") else []) + (plan_shards(rest, q.get("budget", 5400)) if rest else [])
    print(json.dumps(plan, separators=(",", ":")))


sys_path_text = os.path.join(ROOT, "text")
if sys_path_text not in __import__("sys").path:
    __import__("sys").path.insert(0, sys_path_text)
import notes as _notes  # noqa: E402


def line_text(l, work):
    """what the voice reads: the printed line without the editor's notes in brackets, figures in words (text/notes.py)"""
    return speech_text(_notes.spoken(l["text"], work))


def printed_starts(l, work, toks):
    """word starts for every printed word of the line, from tokens of the spoken text: skipped notes get the time of
    the next spoken word, so the read-along stays word-for-word with the page"""
    spoken, counts = _notes.plan(l["text"], work)
    starts, miss = word_starts(spoken, toks)
    if all(c == 1 for c in counts):
        return starts, miss
    return _notes.expand(starts, counts), miss


def speech_text(t):
    """Text as it should be spoken: an all-capitals opening word ("ALL men by nature...") is read as a word."""
    return re.sub(r"^([\"“‘'(]*)([A-Z]{2,})(?=\b)", lambda m: m.group(1) + m.group(2).capitalize(), t)
