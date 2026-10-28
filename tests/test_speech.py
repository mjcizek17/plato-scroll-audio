"""What the voices are given to read, checked against what the page prints.
Run: python3 tests/test_speech.py            (fast cases)
     python3 tests/test_speech.py --corpus   (every line of every script: the mapping must stay word-for-word)
The produce workflow runs both before any rendering."""
import glob, json, os, re, sys
import numbers  # noqa: F401  the stdlib module torch loads first on a runner: our modules must not share its name

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "text"))
sys.path.insert(0, os.path.join(ROOT, "engines"))
import notes as N  # noqa: E402
from script import printed_starts  # noqa: E402

CASES = [
    # figures and dates
    ("The time of the dialogue is 129 B.C., just after.", "The time of the dialogue is one hundred and twenty-nine B C., just after."),
    ("Laelius, born in 186 B.C., was consul in 140.", "Laelius, born in one hundred and eighty-six B C., was consul in one hundred and forty."),
    ("(c. 570 – c. 478 BCE).", "(circa five hundred and seventy – circa four hundred and seventy-eight B C E)."),
    ("His 5,040 citizens; the 4th book; 21st; in 1864; 2,000 men; 1000 men; 1453; 2005; 12.5.",
     "His five thousand and forty citizens; the fourth book; twenty-first; in eighteen sixty-four; two thousand men; one thousand men; fourteen fifty-three; two thousand and five; twelve point five."),
    ("Epicurus (341 BC–270 B.C.) wrote 46‑44 B.C.", "Epicurus (three hundred and forty-one B C to two hundred and seventy B C.) wrote forty-six to forty-four B C."),
    ("Jerome, Commentary on Matthew 27:45: and 8:4::4:2.", "Jerome, Commentary on Matthew twenty-seven, forty-five: and eight to four as four to two."),
    ("Then 5×4 = 20 and 1/2 of 40% is 20%; 3×7=21; 1+3=4; 2)8128; £870; 36½.",
     "Then five times four equals twenty and one half of forty per cent is twenty per cent; three times seven equals twenty-one; one plus three equals four; two into eight thousand one hundred and twenty-eight; eight hundred and seventy pounds; thirty-six and a half."),
    # Roman numerals
    ("Book II of the Laws; Henry VIII; vol. VI (1865); Caput XIII. Next", "Book two of the Laws; Henry eight; volume six (eighteen sixty-five); Caput thirteen. Next"),
    ("II. Alas, how thy dull mind is cast down.", "Alas, how thy dull mind is cast down."),
    ("the case that AB equals CD; (iii) 'privatives'", "the case that AB equals CD; (three) 'privatives'"),
    # abbreviations
    ("i.e. the forms, viz. fire, &c. Mr. Taylor and St. Paul met Dr. Johnson; the MSS. differ; e.g. this; fl. 480; b. 160, d. 210; etc. Then",
     "that is the forms, namely fire, et cetera. Mister Taylor and Saint Paul met Doctor Johnson; the manuscripts differ; for example this; flourished four hundred and eighty; born one hundred and sixty, died two hundred and ten; et cetera. Then"),
    # footnote marks, signs
    ("a burden to the earth.”10 Do you; like a citadel3 — is; called 279Kronos, which; otherness.* But; * * * Then; {} Look",
     "a burden to the earth.” Do you; like a citadel — is; called Kronos, which; otherness. But; Then; Look"),
    # editor's notes, locators, brackets
    ("You are like Alcibiades (Compare Symp.), whom I loved (Greek).", "You are like Alcibiades, whom I loved."),
    ("596 1 1 Archidamus left 2 sons. 45 Labour at these things.", "Archidamus left two sons. forty-five Labour at these things."),
    ("of Menelaus [and found him feasting]. Then he spoke.", "of Menelaus Then he spoke."),
    ("only from hearsay.’(61 E) For I, to answer; (Syrianus ten, 22)Philolaus says; the lyre. R. P. 34.E Men do not",
     "only from hearsay.’ For I, to answer; (Syrianus ten, twenty-two Philolaus says; the lyre. Men do not"),
    # Greek
    ("the letter Π, the “hidden” τὸ κρύφιον; ὁ λόγος; Dæmons", "the letter pi, the “hidden” to kruphion; ho logos; Daemons"),
    # capitals
    ("1 1 THERE is an ancient belief; THE FIRST BOOK", "There is an ancient belief; the first book"),
    ("— THIS is the grove. THEY alone saw it.", "— This is the grove. THEY alone saw it."),
    ("(ii.) SUBJECT-MATTER. The 2 B.C. and 3 A.D. wars; 44 BC; 300 CE; the 2nd MS. reads", "Subject-matter. The two B C. and three A D. wars; forty-four B C; three hundred C E; the second manuscript reads"),
]
# section numbers after a sentence are only silent in editions that print them
CASES_PLUT = [("of doubt.” 2 But after. 300 Spartans fell.", "of doubt.” But after. Spartans fell."),
              ("by asking your own 100,1 questions", "by asking your own questions")]


def check_line(text, work):
    spoken, counts = N.plan(text, work)
    words = text.split()
    assert len(counts) == len(words), (work, text)
    assert len(spoken.split()) == sum(counts), (work, text, spoken)
    toks = [(w, float(i)) for i, w in enumerate(spoken.split())]
    starts, _ = printed_starts({"text": text, "entry": 0}, work, toks)
    assert len(starts) == len(words), (work, text)
    assert all(b >= a for a, b in zip(starts, starts[1:])), (work, text)
    return spoken


def main(corpus=False):
    bad = 0
    for printed, want in CASES:
        got = check_line(printed, "x")
        if got != want:
            bad += 1; print("FAIL\n  printed:", printed, "\n  want:   ", want, "\n  got:    ", got)
    for printed, want in CASES_PLUT:
        got = check_line(printed, "plut-lives-1")
        if got != want:
            bad += 1; print("FAIL (plut)\n  printed:", printed, "\n  want:   ", want, "\n  got:    ", got)
    print(f"{len(CASES) + len(CASES_PLUT) - bad}/{len(CASES) + len(CASES_PLUT)} cases pass")
    if corpus:
        n = digits = 0
        for f in sorted(glob.glob(os.path.join(ROOT, "scripts", "*.json"))):
            d = json.load(open(f, encoding="utf-8"))
            if not isinstance(d, dict) or not d.get("parts") or d["key"].startswith("index"):
                continue
            for p in d["parts"]:
                for l in p["lines"]:
                    n += 1
                    sp = check_line(l["text"], d["key"])
                    if re.search(r"\d", sp):
                        digits += 1
        print(f"corpus: {n} lines mapped word for word; {digits} lines still have a figure in them (OCR slips, algebra)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main("--corpus" in sys.argv)
