"""Editorial notes printed inside the text that the recordings must not read aloud.

Translations carry the editor's apparatus in round brackets in the running text: cross-references ("(Compare Symp.)",
"(cp. Rep.)"), bare references ("(Il.)", "(Arist. Pol.)"), placeholders where the printed Greek was dropped
("(Greek)") and translator's notes ("(Or, reading ...)", "(Probably in allusion to ...)", "(The reading is here
uncertain.)"). The reader shows them; the narrator skips them.

notes(text, work) -> [(start_char, end_char, category)] for each bracket to skip
silent_mask(text, work) -> one bool per whitespace word: True = not spoken
plan(text, work) -> (spoken text, spoken-word count per printed word): notes dropped, figures written out in words
spoken(text, work) -> the spoken text alone

The read-along keeps every word of the printed text: a skipped word gets the start time of the next spoken word, so
the highlight passes over it. The recording tools use these functions, so a note in a new script is never read;
tools/lint_notes.py lists what is skipped, and any bracket that looks like a note but is not caught, for review.

Kept: the speaker's own asides ("(for I was certain that ...)"), glosses that are part of the argument (Cratylus'
etymologies: "(aei thei peri tou aera reon)", "(the son of good fortune)"), and anything not matching a rule below."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figures as _numbers  # noqa: E402  (text/figures.py: figures written out; not "numbers", which clashes with the stdlib module)
import speak_fix as _caps  # noqa: E402  (all-capitals words read as words)

PAREN = re.compile(r"\((?:[^()]|\([^()]*\))*\)")

REF = re.compile(r"^\(\s*(?:compare|comp\.|cp\.|cf\.|see\s+(?:index|above|below|note|[A-Z][a-z]*\.)|vide)\b", re.I)
# "(Il.)", "(Od.)", "(Arist. Pol.)", "(Rep. vii.)", "(Hes. Op. 287.)", "(Il. — the line is not found ...)"
ABBR = re.compile(r"^\(\s*(?:[A-Z][a-z]{0,9}\.\s*){1,3}(?:[\divxlcIVXLC.,:;\s]*|\s*[—-].*)\)$")
GREEK = re.compile(r"^\(\s*(?:the\s+)?Greek\s*\)$", re.I)
# translator's and editor's notes, by how they open
NOTE = re.compile(r"""^\(\s*(?:
      Or,\s | Or\s+(?:with|reading|perhaps|rather|possibly|in\b|the\b|‘|') | Reading\s | Omitting\s | Literally\b | Lit\.\s
    | Probably\s | Perhaps\s+(?:an?\s+allusion|in\s+allusion|referring|a\s+reference) | In\s+allusion | An?\s+allusion | Alluding
    | (?:This\s+is\s+)?[Aa]n?\s+untranslatable | \w+,\s+fragm\.
    | (?:Homer|Hesiod|Euripides|Aeschylus|Sophocles|Pindar|Theognis|Thucydides),\s+[A-Z][^()]{0,40}\)$ | A\s+play\s+(?:on|upon) | A\s+pun\b | Untranslatable
    | A\s+proverb | A\s+proverbial | Proverbial | A\s+fragment | Fragm\. | Frag\.
    | (?:Borrowed|Translated|Quoted|Imitated|Cited)\s+by | Quoted\s+from | From\s+(?:the|an?)\s+\w+\s+(?:poem|play|lost)
    | The\s+(?:reading|text|MSS?\.|manuscripts?|passage|words?\s+in\s+(?:the\s+)?(?:Greek|original)|Greek\s+word|English\s+reader|author\s+of\s+these|Homeric\s+word)\b
    | These\s+words\s+are | Some\s+words | There\s+(?:seems|appears)\s+to\s+be\s+(?:some\s+)?(?:error|corruption|a\s+lacuna|something\s+wanting)
    | ‘[^’]{1,40}’\s+was\s+the\s+title | Socrates\s+is\s+intending | The\s+philosopher\s+alone\s+is\s+not\s+subject
    | Note\b | Translator | Tr\.\s | Ed\.\s | Editor
    | (?:about|nearly|rather\s+more\s+than|rather\s+less\s+than)\s+[\d,½¼¾]+\s+(?:pounds|shillings|guineas|dollars)
)""", re.X)
# Jowett's own aside that opens with "Or," is a translator's alternative only when it is the whole bracket; all of
# the above may also be a speaker's words in some works: those works list what to keep.
# Cratylus: the glosses ("(compare omartein, sunienai, ...)") are the argument itself; only the apparatus goes
KEEP = {"crat": re.compile(r"^\(\s*compare\s+[a-z]")}
# loci and line numbers: "(51a)", "(II.74)", "(ll. 1-5)", "(1051b)", "(I.65-70)", "(Kopp pp. 26-27)", "(ad Att. XIII.44)"
LOCUS = re.compile(r"""^\(\s*(?:
      (?:ll?\.|pp?\.|fr\.|frag\.|reproduced)?\s*[\dIVXLC][\dIVXLCa-f.,:;\-–‑\s]*(?:ff\.?)?
    | ad\s+Att\.[^()]* | Ep\.\s+ad\b[^()]* | [^()]*\bpp?\.\s*\d[^()]* | [^()]{1,30}’s\s+translation
    | \w+\.?,\s+[A-Z][a-z]+\.
)\s*\)$""", re.X)
# editions whose running text prints chapter / section numbers after each sentence (".” 2 But…")
LOCATOR_MID = {"plut-lives-1", "plut-lives-2", "plut-lives-3", "plut-lives-4", "plut-lives-5", "plut-moralia-1",
               "cic-finibus", "cic-officiis", "cic-divinatione", "olymp-alc1", "iamb-protrepticus", "hierocles-golden-verses"}
LOCATOR = re.compile(r"(?:^|[.!?”’\")\]]\s)(\d{1,4}(?: \d{1,4}){0,2}) (?=[A-Z“\"‘(])")
NOT_ABBR = re.compile(r"^\(\s*(?:Yes|No|True|Well|Good|Right|Nay|Aye|So|Indeed)\.?\s*\)$", re.I)


def category(t, work=""):
    if GREEK.match(t):
        return "greek"
    if REF.match(t) and (len(t.split()) <= 8 or re.match(r"^\(\s*(?:compare|cp\.|cf\.)\s+[A-Z][a-z]*\.", t, re.I)):
        return "reference"
    if LOCUS.match(t) and (re.search(r"[.\-–‑]|\d\d", t)) and not re.match(r"^\(\s*(?:\d{1,2}\.?|[ivxIVX]{1,3}\.?|[a-z]|1[5-9]\d\d|20\d\d)\s*\)$", t):
        return "reference"
    if ABBR.match(t) and not NOT_ABBR.match(t):
        return "reference"
    if NOTE.match(t):
        return "note"
    return None


def notes(text, work=""):
    base = re.sub(r"-[a-z]$", "", work or "")
    keep = KEEP.get(base)
    out = []
    for m in PAREN.finditer(text):
        t = m.group(0)
        c = category(t, work)
        if c and not (keep and keep.match(t)):
            out.append((m.start(), m.end(), c))
        elif not c:   # a note inside a kept bracket: "(sema (compare Phaedr.))"
            for n in PAREN.finditer(t, 1, len(t) - 1):
                c = category(n.group(0), work)
                if c:
                    out.append((m.start() + n.start(), m.start() + n.end(), c))
    return out


def silent_mask(text, work=""):
    """one flag per printed word: True = not spoken (an editor's note, or a page / section / verse number)"""
    spans = notes(text, work)
    # square brackets are the editor's too ("[and found him feasting]"): the page does not light them, so they are not read
    spans += [(m.start(), m.end(), "bracket") for m in re.finditer(r"\[[^\]]*\]", text)]
    # bare figures that are the edition's page, chapter, section or verse numbers, not the author's words: at the start
    # of a line ("596 1 1 Archidamus...") or after a sentence (".” 2 But after..."), before a capitalised word
    for m in LOCATOR.finditer(text):
        before = text[: m.start(1)].rstrip()
        mid = m.start(1) > 0
        if mid and (re.sub(r"-[a-z]$", "", work or "") not in LOCATOR_MID):
            continue   # a figure after a full stop is a section number only in editions that print them
        if mid and re.search(r"(?:^|\s)(?:c|ca|p|pp|l|ll|vol|no|fl|b|d|r|lib|cap|ch|i\.e|e\.g|etc|viz|cf|St|Mt|Dr|Mr|Mrs|Prof)\.$", before):
            continue   # "c. 478": the full stop is an abbreviation's
        if re.match(r"^(?:BC|BCE|AD|CE|B\.C|A\.D)\b", text[m.end():].lstrip()):
            continue   # "478 BCE": a date
        spans.append((m.start(1), m.end(1), "locator"))
    mask, pos = [], 0
    for w in text.split():
        i = text.index(w, pos); j = i + len(w); pos = j
        # a word is silent when its letters lie inside a note ("Symp.)," -> the comma goes with it)
        core = re.search(r"[0-9A-Za-zÀ-ÿ]", w)
        k = i + (core.start() if core else 0)
        mask.append(any(a <= k < b for a, b, _ in spans))
    return mask


def plan(text, work=""):
    """(spoken_text, counts): what the voice reads, and for every printed word how many spoken words stand for it
    (0 = an editor's note, not read; 1 = itself; more = a figure written out, text/figures.py)."""
    mask = silent_mask(text, work)
    base = re.sub(r"-[a-z]$", "", work or "")
    if base not in _caps.GEOMETRY:
        fixed = _caps.fix(text)              # "IT IS, I think" -> "It is, I think" (same words, same count)
        if len(fixed.split()) == len(text.split()):
            text = fixed
    words = text.split()
    out, counts = [], []
    for i, (w, m) in enumerate(zip(words, mask)):
        if m:
            counts.append(0)
            if out:   # keep the sentence's own punctuation that followed the note: "fire (Greek)." -> "fire."
                tail = re.sub(r"^.*\)", "", w)
                if tail and not re.search(r"[0-9A-Za-z]", tail):
                    out[-1] += tail
            continue
        said = _numbers.spoken(w, words[i - 1] if i else "", words[i + 1] if i + 1 < len(words) else "")
        if said is not None and all(len(x.split()) == 1 for x in said):
            out += said
            counts.append(len(said))
            if not said and out:   # a section number dropped mid-line keeps the sentence's punctuation before it
                pass
        else:
            out.append(w)
            counts.append(1)
    # stray square brackets (an editor's insertion that runs over several paragraphs) are not read
    if "[" in text or "]" in text:
        fixed, counts2, j = [], [], 0
        for c in counts:
            toks = out[j: j + c]; j += c
            toks = [re.sub(r"[\[\]]", "", t) for t in toks]
            toks = [t for t in toks if re.search(r"[0-9A-Za-zÀ-ÿ]", t) or not re.fullmatch(r"[\[\]]*", t)]
            fixed += toks; counts2.append(len(toks))
        out, counts = fixed, counts2
    spoken_text = " ".join(out)
    if len(spoken_text.split()) != sum(counts) or len(counts) != len(text.split()):
        return text, [1] * len(text.split())   # never let a bad expansion put the read-along out of step
    return spoken_text, counts


def spoken(text, work=""):
    return plan(text, work)[0]


def expand(starts_spoken, counts, end=None):
    """word start times of the spoken text -> one per printed word: a word spoken as several takes the first one's
    time; a silent word takes the next spoken word's time"""
    it = iter(starts_spoken)
    full = []
    for c in counts:
        if c == 0:
            full.append(None)
        else:
            full.append(next(it))
            for _ in range(c - 1):
                next(it)
    nxt = end if end is not None else max([t for t in full if t is not None], default=0.0)
    for i in range(len(full) - 1, -1, -1):
        if full[i] is None:
            full[i] = nxt
        else:
            nxt = full[i]
    for i in range(1, len(full)):
        full[i] = max(full[i], full[i - 1])
    return full
