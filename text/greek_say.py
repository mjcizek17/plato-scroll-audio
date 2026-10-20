"""Greek words inside English translations are spoken in a simple transliteration (Ἡρόδοτος -> Herodotos), word for
word, so the reader's word count and the read-along timing stay the same. Usage: python text/greek_say.py SCRIPT.json..."""
import json, re, sys, unicodedata
M = dict(zip("αβγδεζηθικλμνξοπρστυφχψωςΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ",
             "a b g d e z e th i k l m n x o p r s t y ph ch ps o s A B G D E Z E Th I K L M N X O P R S T Y Ph Ch Ps O".split()))
GK = re.compile(r"[Ͱ-Ͽἀ-῿]")


def say(word):
    rough = any(unicodedata.decomposition(c).find("0314") >= 0 for c in word[:2])   # rough breathing -> h
    base = "".join(c for c in unicodedata.normalize("NFD", word) if not unicodedata.combining(c))
    out = "".join(M.get(c, c) for c in base)
    if rough and out[:1].isalpha():
        out = ("H" + out[0].lower() if out[0].isupper() else "h" + out[0]) + out[1:]
    return out.replace("gg", "ng").replace("gk", "nk").replace("oy", "ou").replace("Oy", "Ou")


def fix(text):
    if text.strip() == "Ο" or re.search(r"(^|\s)Ο(\s|$)", text):          # Greek capital omicron printed for 'O'
        text = re.sub(r"(^|\s)Ο(?=\s|$)", r"\1O", text)
    return " ".join(say(w) if GK.search(w) else w for w in text.split(" "))


if __name__ == "__main__":
    for f in sys.argv[1:]:
        d = json.load(open(f, encoding="utf-8")); n = 0
        for p in d["parts"]:
            for l in p["lines"]:
                if GK.search(l["text"]):
                    l["text"] = fix(l["text"]); n += 1
        json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        print(f, n, "lines with Greek spoken in transliteration")
