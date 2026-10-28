"""Numbers and dates as the voice should say them.

The voices misread figures ("478" as "578", "186 B.C." as "eighteen-six"), so every figure is written out in words
before it is spoken: "129 B.C." -> "one hundred and twenty-nine B C", "1864" -> "eighteen sixty-four", "5,040" ->
"five thousand and forty", "4th" -> "fourth", "c. 570" -> "circa five hundred and seventy". The printed page is not
changed: the read-along maps each printed word to the first of the words spoken for it (text/notes.py, plan()).

say(word, prev, next) -> list of spoken words for one printed word (whitespace token), or None to leave it alone."""
import re

ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
        "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
ORD = {"one": "first", "two": "second", "three": "third", "five": "fifth", "eight": "eighth", "nine": "ninth",
       "twelve": "twelfth"}

LEAD = re.compile(r"^([\"“‘'(\[]*)(.*?)([\"”’'),\]\.;:!?]*)$", re.S)
ERA = {"B.C.": "B C", "BC": "B C", "B.C.E.": "B C E", "BCE": "B C E", "A.D.": "A D", "AD": "A D", "C.E.": "C E", "CE": "C E"}
NUM = re.compile(r"^(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?$")
ORDINAL = re.compile(r"^(\d+)(st|nd|rd|th)$", re.I)


def _under_thousand(n):
    out = []
    if n >= 100:
        out.append(ONES[n // 100] + " hundred")
        n %= 100
        if n:
            out.append("and")
    if n >= 20:
        t = TENS[n // 10]
        out.append(t + ("-" + ONES[n % 10] if n % 10 else ""))
    elif n:
        out.append(ONES[n])
    return out


def cardinal(n):
    """0..999,999,999 in words, with 'and' (one hundred and twenty-nine)"""
    if n == 0:
        return ["zero"]
    parts = []
    for div, name in ((1_000_000_000, "billion"), (1_000_000, "million"), (1000, "thousand")):
        if n >= div:
            parts += _under_thousand(n // div) + [name]
            n %= div
    if n:
        if parts and n < 100:
            parts.append("and")
        parts += _under_thousand(n)
    return parts


def year(n):
    """1000..2099 the way a year is said: eighteen sixty-four, nineteen hundred, two thousand and five"""
    if 2000 <= n <= 2099:
        return ["two thousand"] + (["and"] + _under_thousand(n - 2000) if n > 2000 else [])
    hi, lo = divmod(n, 100)
    if lo == 0:
        return [ONES[hi] + " hundred"]
    if lo < 10:
        return [ONES[hi], "oh", ONES[lo]]
    return [ONES[hi]] + _under_thousand(lo)


def ordinal(n):
    w = cardinal(n)
    last = w[-1]
    if "-" in last:
        a, b = last.rsplit("-", 1)
        w[-1] = a + "-" + ORD.get(b, b + "th")
    elif last.endswith("y"):
        w[-1] = last[:-1] + "ieth"
    else:
        w[-1] = ORD.get(last, last + "th")
    return w


def _core(word):
    m = LEAD.match(word)
    return m.group(1), m.group(2), m.group(3)


def say(word, prev="", nxt=""):
    """spoken words for one printed word, or None if it is read as printed"""
    lead, core, tail = _core(word)
    if not core:
        return None
    # "c." before a figure: circa
    if core in ("c", "ca") and tail.startswith(".") and re.match(r"^[(\[]*\d", nxt or ""):
        return ["circa"]
    # era abbreviations next to a figure: letters, so "B.C." is never "bee-cee" run together
    key = core if core in ERA else core + "." if core + "." in ERA else None
    if key and (re.search(r"\d", prev or "") or re.search(r"\d", nxt or "")):
        return ERA[key].split()
    m = ORDINAL.match(core)
    if m:
        return ordinal(int(m.group(1)))
    m = NUM.match(core)
    if not m:
        return None
    whole, frac = m.group(1).replace(",", ""), m.group(2)
    if len(whole) > 9:
        return None
    n = int(whole)
    if frac is not None:
        return cardinal(n) + ["point"] + [ONES[int(c)] for c in frac]
    # a year: four figures 1000-2099 without a thousands comma, not before "men", "ships" ... (a count)
    if 1100 <= n <= 2099 and "," not in m.group(1) and not re.match(r"^[a-z]+s\b", nxt or ""):
        return year(n)
    return cardinal(n)


def spoken(word, prev="", nxt=""):
    """the printed word's spoken words with its own punctuation kept ("(129" -> ["(one", "hundred", ...]), or None"""
    said = say(word, prev, nxt)
    if not said:
        return None
    lead, core, tail = _core(word)
    if said == ["circa"]:
        tail = tail[1:]   # the abbreviation's own full stop
    said = list(said)
    said[0] = lead + said[0]
    said[-1] = said[-1] + tail
    return said


def speak_count(text):
    """how many figures in a text would be written out (for the lint report)"""
    ws = text.split()
    return sum(1 for i, w in enumerate(ws) if say(w, ws[i - 1] if i else "", ws[i + 1] if i + 1 < len(ws) else ""))
