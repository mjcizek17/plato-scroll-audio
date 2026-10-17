"""Split narrated text into narration and quotations, at whitespace so word counts never change.
segments(text) -> [(kind, text)] with kind 'narr' or 'quote'. A quotation runs from a word containing an
opening “ to the word containing its closing ”; an unclosed quotation runs to the end of the entry
(the convention for a speech that continues into the next paragraph)."""


def segments(text):
    words = text.split()
    out, cur, kind, depth = [], [], "narr", 0
    for w in words:
        opens = w.count("“"); closes = w.count("”")
        if kind == "narr" and opens:
            if cur:
                out.append(("narr", " ".join(cur))); cur = []
            kind = "quote"
            depth = opens - closes
            cur.append(w)
            if depth <= 0:
                out.append(("quote", " ".join(cur))); cur, kind, depth = [], "narr", 0
            continue
        cur.append(w)
        if kind == "quote":
            depth += opens - closes
            if depth <= 0:
                out.append(("quote", " ".join(cur))); cur, kind, depth = [], "narr", 0
    if cur:
        out.append((kind, " ".join(cur)))
    return out


def marked(text):
    """Text with each quotation wrapped as [1]…[/1] for labelling, and the number of quotations."""
    parts, n = [], 0
    for kind, t in segments(text):
        if kind == "quote":
            n += 1; parts.append(f"[{n}]{t}[/{n}]")
        else:
            parts.append(t)
    return " ".join(parts), n


if __name__ == "__main__":
    s = "“Well,” said he, “do you see how many of us there are?” “Of course I do.” Then Polemarchus said, “Stay"
    print(segments(s)); print(marked(s))
