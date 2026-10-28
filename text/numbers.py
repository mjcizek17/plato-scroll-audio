"""What the voice should say for the things it misreads: figures, dates, Roman numerals, abbreviations, symbols,
footnote marks, Greek letters. The printed page is never changed; text/notes.py plan() maps each printed word to
the words spoken for it, so the read-along keeps one time per printed word.

  "129 B.C."        one hundred and twenty-nine B C      "1864"          eighteen sixty-four
  "5,040"           five thousand and forty              "4th"           fourth
  "c. 570"          circa five hundred and seventy       "341–270"       three hundred and forty-one to two hundred and seventy
  "Book II"         Book Two                             "II. Alas"      Alas  (a section number: not read)
  "i.e."            that is                              "viz."          namely
  "&c."             et cetera                            "5×4 = 20"      five times four equals twenty
  "earth.”10"       earth.”  (a footnote mark: not read) "citadel3"      citadel
  "Π"               pi                                   "τὸ κρύφιον"    to kruphion
  "Dæmons"          Daemons                              "27:45"         twenty-seven, forty-five

spoken(word, prev, next) -> list of spoken words for one printed word (whitespace token), [] when nothing is said
for it, or None when it is read as printed. Everything here must keep working on text it has never seen: when in
doubt, leave the word alone."""
import re
import unicodedata

ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
        "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
ORD = {"one": "first", "two": "second", "three": "third", "five": "fifth", "eight": "eighth", "nine": "ninth",
       "twelve": "twelfth"}

LEAD = re.compile(r"^([\"“‘'(\[]*)(.*?)([\"”’'),\]\.;:!?]*)$", re.S)
ERA = {"B.C.": "B C", "BC": "B C", "B.C.E.": "B C E", "BCE": "B C E", "A.D.": "A D", "AD": "A D", "C.E.": "C E", "CE": "C E"}
NUM = re.compile(r"^(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?$")
ORDINAL = re.compile(r"^(\d{1,3}(?:,\d{3})+|\d+)(st|nd|rd|th)$", re.I)
# printed words the scans got wrong (Taylor's Iamblichus, Theon)
OCR = {"1’im:xus": "Timaeus", "circumvo1ve": "circumvolve", "de6ates": "debates", "2l3": "", "First1KGreek": "First Thousand Greek",
       "Pythagoreomm": "Pythagoreorum"}
ROMAN = re.compile(r"^(?=[IVXLC])M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$")
# words after which a Roman numeral is a number ("Book II", "Henry VIII", "vol. VI")
NUMBERED = re.compile(r"^[(\[\"“]*(?:Book|Books|Chapter|Chapters|Part|Parts|Section|Letter|Epistle|Hymn|Ode|Fragment|Fragments|"
                      r"Chap|Ch|Proposition|Prop|Tetralogy|Ennead|Tractate|Treatise|Volume|Vol|vol|Act|Scene|Canto|Idyll|Satire|"
                      r"Eclogue|Georgic|Oration|Dissertation|Dialogue|Lecture|Psalm|Question|Article|Lib|lib|Tom|tom|Cap|cap|No|no|Num|"
                      r"Henry|Edward|Richard|George|Charles|Louis|Philip|Ptolemy|Antiochus|Seleucus|Darius|Artaxerxes|Pius|Leo|"
                      r"Gregory|John|Paul|Urban|Clement|Innocent|Benedict|Alexander|Constantine|Theodosius|Justinian|Attalus|Mithridates|"
                      r"Olympian|Pythian|Nemean|Isthmian|Iliad|Odyssey|Aeneid|Metamorphoses|Enneads|Letters|Satires|Epistles|Odes|"
                      r"Republic|Laws|Politics|Ethics|Metaphysics|Physics|Elements|Lives|Moralia|Stromateis|Tusculans|Caput|Sectio|Liber|Pars)\.?$")
# an abbreviation is read as its words; its trailing full stop is not a sentence end unless a capital follows
ABBREV = {"i.e": "that is", "e.g": "for example", "viz": "namely", "etc": "et cetera", "&c": "et cetera", "vs": "versus",
          "sc": "namely", "scil": "namely", "ibid": "in the same place", "cf": "compare", "fl": "flourished", "ca": "circa",
          "lib": "book", "cap": "chapter", "chap": "chapter", "ch": "chapter", "chs": "chapters", "bk": "book", "sect": "section",
          "vol": "volume", "vols": "volumes", "tom": "volume", "pp": "pages", "ll": "lines",
          "no": "number", "nos": "numbers", "ed": "edition", "edd": "editions", "trans": "translated", "tr": "translated",
          "fr": "fragment", "frag": "fragment", "fragm": "fragment", "St": "Saint", "Mt": "Mount", "Dr": "Doctor", "Mr": "Mister",
          "Mrs": "Missus", "Prof": "Professor", "Rev": "Reverend", "Hon": "Honourable", "Esq": "Esquire", "op": "opus",
          "cent": "century", "MS": "manuscript", "MSS": "manuscripts", "Arist": "Aristotle",
          "8vo": "octavo", "4to": "quarto", "12mo": "duodecimo", "16mo": "sixteenmo", "18mo": "eighteenmo", "fol": "folio"}
# single letters that are a reference only before a figure ("b. 186", "d. 43", "p. 220", "l. 5")
DATE_ABBREV = {"b": "born", "d": "died", "r": "reigned", "p": "page", "l": "line", "c": "circa", "ca": "circa", "fl": "flourished"}
SYMBOLS = {"&": "and", "=": "equals", "+": "plus", "×": "times", "÷": "divided by", "%": "per cent", "§": "section", "#": "number",
           "§§": "sections", "¶": "paragraph", "°": "degrees", "→": "to", "∴": "therefore", "∞": "infinity", "∝": "proportional to",
           "−": "minus"}
GREEK = {"α": "a", "β": "b", "γ": "g", "δ": "d", "ε": "e", "ζ": "z", "η": "e", "θ": "th", "ι": "i", "κ": "k", "λ": "l",
         "μ": "m", "ν": "n", "ξ": "x", "ο": "o", "π": "p", "ρ": "r", "σ": "s", "ς": "s", "τ": "t", "υ": "u", "φ": "ph",
         "χ": "ch", "ψ": "ps", "ω": "o", "ϕ": "ph", "ϑ": "th", "ϛ": "st", "ϰ": "k", "ϱ": "r", "ϐ": "b", "ϗ": "kai"}
GREEK_NAME = {"α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon", "ζ": "zeta", "η": "eta", "θ": "theta",
              "ι": "iota", "κ": "kappa", "λ": "lambda", "μ": "mu", "ν": "nu", "ξ": "xi", "ο": "omicron", "π": "pi", "ρ": "rho",
              "σ": "sigma", "ς": "sigma", "τ": "tau", "υ": "upsilon", "φ": "phi", "χ": "chi", "ψ": "psi", "ω": "omega",
              "ϕ": "phi", "ϑ": "theta", "ϰ": "kappa", "ϱ": "rho", "ϐ": "beta"}
FRACTION = {"1/2": "one half", "1/3": "one third", "2/3": "two thirds", "1/4": "one quarter", "3/4": "three quarters",
            "1/5": "one fifth", "1/8": "one eighth"}
GREEK_RANGE = r"[Ͱ-Ͽἀ-῿]"


def _under_thousand(n):
    out = []
    if n >= 100:
        out += [ONES[n // 100], "hundred"]
        n %= 100
        if n:
            out.append("and")
    if n >= 20:
        out.append(TENS[n // 10] + ("-" + ONES[n % 10] if n % 10 else ""))
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
    """1100..2099 the way a year is said: eighteen sixty-four, nineteen hundred, two thousand and five"""
    if 2000 <= n <= 2099:
        return ["two", "thousand"] + (["and"] + _under_thousand(n - 2000) if n > 2000 else [])
    hi, lo = divmod(n, 100)
    if lo == 0:
        return [ONES[hi], "hundred"]
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


def roman(s):
    v = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    n = 0
    for i, ch in enumerate(s):
        n += -v[ch] if i + 1 < len(s) and v[ch] < v[s[i + 1]] else v[ch]
    return n


def greek(word):
    """a Greek word in Latin letters (rough breathing -> h), a lone letter by its name"""
    nfd = unicodedata.normalize("NFD", word)
    rough = "\u0314" in nfd
    base = "".join(ch for ch in nfd if not unicodedata.combining(ch)).lower()
    if len(base) == 1 and base in GREEK_NAME and not rough:
        return GREEK_NAME[base]
    out = "".join(GREEK.get(ch, ch) for ch in base)
    return ("h" + out) if rough else out


def _core(word):
    m = LEAD.match(word)
    return m.group(1), m.group(2), m.group(3)


def _number_words(core, nxt):
    """a plain figure, ordinal, decimal or year -> words, or None"""
    m = ORDINAL.match(core)
    if m:
        return ordinal(int(m.group(1).replace(",", "")))
    m = NUM.match(core)
    if not m:
        return None
    whole, frac = m.group(1).replace(",", ""), m.group(2)
    if len(whole) > 9:   # beyond the billions: digit by digit
        return [ONES[int(ch)] + ("," if i % 3 == 2 and i + 1 < len(whole) else "") for i, ch in enumerate(whole)]
    n = int(whole)
    if frac is not None:
        return cardinal(n) + ["point"] + [ONES[int(c)] for c in frac]
    if 1100 <= n <= 2099 and "," not in m.group(1) and not re.match(r"^[a-z]+s\b", nxt or ""):
        return year(n)
    return cardinal(n)


def say(word, prev="", nxt=""):
    """spoken words for the core of one printed word (its punctuation is handled by spoken()): a list, [] for
    nothing, or None when it is read as printed"""
    lead, core, tail = _core(word)
    if not core:
        return None
    # known OCR slips in the scanned editions (a printed word -> the word meant)
    if core in OCR:
        return OCR[core].split()
    # OCR's signs for × between figures (⟩ «), a stray brace after a figure, a comma-glued footnote letter (4096,t)
    if re.search(r"\d", core):
        core = re.sub(r"(?<=\d)[⟩«](?=\d|$)", "×", core).rstrip("}{")
        core = re.sub(r"^(\d[\d,]*),[a-z]$", r"\1", core)
    nxt_fig = bool(re.match(r"^[(\[]*\d", nxt or ""))
    # a lone "x" between figures is the multiplication sign ("21 x 20")
    if core == "x" and re.search(r"\d$", prev or "") and nxt_fig:
        return ["times"]
    # "5040/(21" : a fraction whose denominator opens a bracket
    m = re.match(r"^(\d[\d,]*)/\((\d+)$", core)
    if m:
        return cardinal(int(m.group(1).replace(",", ""))) + ["over"] + cardinal(int(m.group(2)))
    # folios: 17r. 41v
    m = re.match(r"^(\d+)([rv])$", core)
    if m and re.search(r"\bfol\.?$", prev or ""):
        return cardinal(int(m.group(1))) + [{"r": "recto", "v": "verso"}[m.group(2)]]
    # "5-6-7": numbered items run together
    if re.fullmatch(r"\d+(-\d+){2,}", core):
        out = []
        for i, piece in enumerate(core.split("-")):
            out += cardinal(int(piece)); out[-1] += "," if i < core.count("-") else ""
        return out
    # a figure with one stray letter glued to it (OCR: "3s"): the figure
    if re.fullmatch(r"\d+[a-z]", core) and core not in ABBREV and not re.fullmatch(r"\d+(st|nd|rd|th)", core):
        return cardinal(int(core[:-1]))
    # a "word" of signs only ({}, \, ***, <>) is nothing; dashes and dots stay (they are pauses)
    if not re.search(r"[0-9A-Za-zÀ-ÿ\u0370-\u03FF\u1F00-\u1FFF]", core) and not re.fullmatch(r"[—–\-.…·]+", core) and core not in SYMBOLS:
        return []
    # footnote marks and stray signs: * † ‡ | glued to a word are not read; a word made of them is nothing
    if re.search(r"[*†‡|]", core):
        core2 = re.sub(r"[*†‡|]", "", core)
        if not re.search(r"[A-Za-z0-9]", core2):
            return []
        if re.fullmatch(r"\d{1,3}", core2):   # "|58": a page mark
            return []
        return say(lead + core2 + tail, prev, nxt) or [core2]
    # a footnote number before a word (279Kronos, 281”all), or after a short one (to204)
    m = re.match(r"^(\d{1,3})([\"”’']*)([A-Za-z][A-Za-z’'-]+)$", core)
    if m and m.group(3) != "ff" and core not in ABBREV and not re.fullmatch(r"\d+(st|nd|rd|th)", core):
        return [m.group(2) + m.group(3)]
    m = re.match(r"^([A-Za-z]{2})(\d{2,3})$", core)
    if m:
        return [m.group(1)]
    m = re.match(r"^(\d+)([A-Z])$", core)   # "(91A)": a fragment number
    if m and lead.endswith("("):
        return cardinal(int(m.group(1))) + [m.group(2)]
    if re.fullmatch(r"[—–]\d{1,3}", core):   # "—3": a footnote mark after a dash
        return ["—"]
    # labels of the edition: "1.a." (Jowett's Parmenides hypotheses), "114B–" (Olympiodorus' lemmata)
    if re.fullmatch(r"\d+\.[a-z]{1,2}", core) and tail.startswith("."):
        return []
    if re.fullmatch(r"\d{2,3}[A-E][–-]?", core):
        return []
    # "95ff" and following; "3.5.7." a series; "36½"; "1X2X3"; "them.-(5)"; "(91A)"; "1/2B"
    m = re.match(r"^(\d+)ff$", core)
    if m:
        return cardinal(int(m.group(1))) + ["and", "following"]
    if re.fullmatch(r"(\d+\.){2,}\d+", core):   # "3.5.7" a series ("12.5" is a decimal)
        out = []
        for n in core.split("."):
            w = cardinal(int(n)); w[-1] += ","; out += w
        out[-1] = out[-1].rstrip(",")
        return out
    m = re.match(r"^(\d+)?([½¼¾])$", core)
    if m:
        frac = {"½": ["a", "half"], "¼": ["a", "quarter"], "¾": ["three", "quarters"]}[m.group(2)]
        return (cardinal(int(m.group(1))) + ["and"] if m.group(1) else []) + frac
    if re.fullmatch(r"\d+(X\d+)+", core):
        out = []
        for i, n in enumerate(core.split("X")):
            out += (["times"] if i else []) + cardinal(int(n))
        return out
    m = re.match(r"^(.+?)([.,;:]?)-\((\d+)$", core)   # "them.-(5)" (the ")" is in the tail)
    if m and tail.startswith(")"):
        w = cardinal(int(m.group(3))); w[0] = "(" + w[0]
        return [m.group(1) + m.group(2)] + w
    m = re.match(r"^(\d+)/(\d+)([A-Z])$", core)
    if m:
        f = FRACTION.get(m.group(1) + "/" + m.group(2))
        return (f.split() if f else cardinal(int(m.group(1))) + ["over"] + cardinal(int(m.group(2)))) + [m.group(3)]
    # two words joined by "=": huphistasthai=substare
    m = re.match(r"^([A-Za-z]+)=([A-Za-z]+)$", core)
    if m:
        return [m.group(1), "equals", m.group(2)]
    # ratios and verses: 8:4::4:2 (eight to four as four to two); Matthew 27:45 (twenty-seven, forty-five); II:12
    m = re.match(r"^(\d+):(\d+)(?:::(\d+):(\d+))?$", core)
    if m:
        verse = bool(re.match(r"^[(\[\"“]*[A-Z][a-z]+[,.]?$|^[IVX]+[,.:]?$", prev or ""))
        if m.group(3) or not verse:
            out = cardinal(int(m.group(1))) + ["to"] + cardinal(int(m.group(2)))
            if m.group(3):
                out += ["as"] + cardinal(int(m.group(3))) + ["to"] + cardinal(int(m.group(4)))
            return out
    m = re.match(r"^([IVX]+):(\d+)$", core)
    if m and ROMAN.match(m.group(1)):
        a = cardinal(roman(m.group(1))); a[-1] += ","
        return a + cardinal(int(m.group(2)))
    # "100,1" (page and line in Olympiodorus), "27b." at a line start: references, not read
    if re.fullmatch(r"\d{1,3},\d{1,2}", core):
        return []
    if re.fullmatch(r"\d{1,3}[a-z]", core) and tail.startswith(".") and not prev:
        return []
    m = re.match(r"^#(\d+)$", core)   # "Fragment #10"
    if m:
        return ["number"] + cardinal(int(m.group(1)))
    # "£870", "273d" (a Stephanus page), "2's", "1-itself"
    m = re.match(r"^£(\d[\d,]*)$", core)
    if m and NUM.match(m.group(1)):
        return cardinal(int(m.group(1).replace(",", ""))) + ["pounds"]
    m = re.match(r"^(\d+)([a-e])$", core)
    if m:
        return cardinal(int(m.group(1))) + [m.group(2)]
    m = re.match(r"^(\d+)('s|-[a-z]+)$", core)
    if m:
        w = cardinal(int(m.group(1))); w[-1] += m.group(2)
        return w
    # arithmetic written with signs: 3×7=21, +1=17, 2)8128 (two into eight thousand…)
    if re.fullmatch(r"[+\-−×=)(]*\d[\d+\-−×=)(,—]*", core) and re.search(r"[+−×=)—]", core):
        out = []
        for piece in re.findall(r"\d[\d,]*|[+\-−×=)(—]", core):
            if piece[0].isdigit():
                w = _number_words(piece, "")
                out += w if w else [piece]
            else:
                out += {"+": ["plus"], "-": ["minus"], "−": ["minus"], "×": ["times"], "=": ["equals"], ")": ["into"], "(": [], "—": ["equals"]}[piece]
        return out
    # footnote marks: digits glued to the end of a word or after its closing punctuation (earth.”10, citadel3)
    m = re.match(r"^(.*[A-Za-z])([\"”’'),.;:!?]*)(\d{1,3})$", core)
    if m and not re.search(r"\d", m.group(1)) and len(re.sub(r"[^A-Za-z]", "", m.group(1))) >= 3:
        return [m.group(1) + m.group(2)]
    # Greek letters: in Latin letters, a lone letter by name; a Greek letter inside a Latin word is an OCR slip (IΝ, οf)
    if re.search(GREEK_RANGE, core):
        if re.search(r"[A-Za-z]", core):
            return [re.sub(GREEK_RANGE, lambda m: GREEK.get(unicodedata.normalize("NFD", m.group(0))[0].lower(), ""), core)]
        parts = re.split(r"(" + GREEK_RANGE + r"[" + GREEK_RANGE[1:-1] + r"\u0300-\u036F]*)", core)
        return ["".join(greek(p) if re.search(GREEK_RANGE, p) else p for p in parts if p)]
    # ligatures
    if any(ch in core for ch in "æœÆŒ"):
        return [core.replace("æ", "ae").replace("œ", "oe").replace("Æ", "Ae").replace("Œ", "Oe")]
    # era abbreviations next to a figure
    key = core if core in ERA else core + "." if core + "." in ERA else None
    if key and (nxt_fig or re.search(r"\d", prev or "")):
        return ERA[key].split()
    # abbreviations (their own full stop is in the tail)
    if tail.startswith("."):
        if core in DATE_ABBREV and nxt_fig:
            return [DATE_ABBREV[core]]
        if core in ABBREV:
            return ABBREV[core].split()
        if core.lower() in ABBREV and core.lower() not in ("st", "mt", "dr", "mr", "mrs", "prof", "rev", "hon", "esq", "ms", "mss", "arist"):
            return ABBREV[core.lower()].split()
    if core in ("i.e", "e.g") or (core in ABBREV and re.match(r"^\d", core)):   # 8vo, 4to
        return ABBREV[core].split()
    m = re.match(r"^(.+)-(viz|i\.e|e\.g|etc)$", core)   # "doer-viz."
    if m:
        return [m.group(1)] + ABBREV[m.group(2)].split()
    if core == "&c":
        return ["et", "cetera"]
    # symbols on their own
    if core in SYMBOLS:
        return SYMBOLS[core].split()
    # Roman numerals: after "Book", "Henry", "vol." a number; alone at the start of a line or sentence a section
    # number, not read; anywhere else left as printed (CD, DC, LI... may be letters or labels)
    if ROMAN.match(core) and core != "I":
        if NUMBERED.match(prev or ""):
            return cardinal(roman(core))
        if tail.startswith(".") and (not prev or re.search(r"[.!?”’\"]$", prev)):
            return []   # "II. Alas…"
    if lead.endswith("(") and re.match(r"^[ivxlIVXL]{1,6}\.?$", core) and ROMAN.match(core.upper().rstrip(".")):
        if tail.startswith(")") and not core.endswith("."):
            return cardinal(roman(core.upper()))   # "(iii)" in a list
        if (core.endswith(".") or "." in tail[:2]) and (not prev or re.search(r"[.!?”’\"]$", prev)):
            return []   # "(ii.) SUBJECT-MATTER": a section label
    # fractions, ranges, sums, verses: 1/2, 341–270, 5×4, 27:45, 40%
    if core in FRACTION:
        return FRACTION[core].split()
    m = re.match(r"^(\d+)/(\d+)$", core)
    if m:
        return cardinal(int(m.group(1))) + ["over"] + cardinal(int(m.group(2)))
    m = re.match(r"^([A-Za-z.]*)(\d[\d,.]*)([–‑-])(\d[\d,.]*)$", core)
    if m:
        a, b = _number_words(m.group(2), ""), _number_words(m.group(4), "")
        if a and b:
            return ([m.group(1)] if m.group(1) else []) + a + ["to"] + b
    m = re.match(r"^(\d+)([×+=−])(\d+)$", core)
    if m:
        return cardinal(int(m.group(1))) + SYMBOLS[m.group(2)].split() + cardinal(int(m.group(3)))
    m = re.match(r"^(\d+):(\d+)$", core)
    if m:
        a = cardinal(int(m.group(1))); a[-1] += ","
        return a + cardinal(int(m.group(2)))
    m = re.match(r"^(B\.?C\.?E?\.?|A\.?D\.?|CE)([–‑-])(\d+)$", core)   # "341 BC–270"
    if m and m.group(1) in ERA or (m and m.group(1) + "." in ERA):
        return ERA[m.group(1) if m.group(1) in ERA else m.group(1) + "."].split() + ["to"] + cardinal(int(m.group(3)))
    if core.endswith("%") and NUM.match(core[:-1]):
        return cardinal(int(core[:-1].replace(",", ""))) + ["per", "cent"]
    # "c." before a figure: circa
    if core in ("c", "ca") and tail.startswith(".") and nxt_fig:
        return ["circa"]
    return _number_words(core, nxt)


def spoken(word, prev="", nxt=""):
    """the printed word's spoken words with its own punctuation kept ("(129" -> ["(one", "hundred", ...]), [] when
    nothing is said for it, or None when it is read as printed"""
    said = say(word, prev, nxt)
    if said is None:
        return None
    lead, core, tail = _core(word)
    if said == []:
        return []
    said = list(said)
    # the full stop of an abbreviation is not a sentence end unless a capital follows
    abbrev = core in ABBREV or core.lower() in ABBREV or core in DATE_ABBREV or said == ["circa"] or (ROMAN.match(core) and NUMBERED.match(prev or ""))
    title = core in ("St", "Mt", "Dr", "Mr", "Mrs", "Prof", "Rev", "Hon", "Esq")
    n0 = re.sub(r"^[(\[\"“]*", "", nxt or "")
    continues = not re.match(r"^[A-Z“\"(]", nxt or "") or ROMAN.match(re.sub(r"[^A-Z]", "", n0)[:6] or "-") or re.match(r"^\d", n0) or n0.split(".")[0] in ERA or n0 in ERA
    if tail.startswith(".") and abbrev and (title or continues):
        tail = tail[1:]
    said[0] = lead + said[0]
    said[-1] = said[-1] + tail
    return said


def speak_count(text):
    """how many words of a text are spoken differently from the page (for the lint report)"""
    ws = text.split()
    return sum(1 for i, w in enumerate(ws) if spoken(w, ws[i - 1] if i else "", ws[i + 1] if i + 1 < len(ws) else "") is not None)
