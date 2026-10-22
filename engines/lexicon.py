"""Name pronunciations for Kokoro, per accent. Traditional English classicist pronunciation
(Jones / OED conventions). 'gb' = British phonemes, 'us' = American phonemes.
Add a name here whenever a listener flags it; possessives (X's) are derived automatically."""
import re

GB = {
    "Socrates": "sˈɒkɹətiːz", "Alcibiades": "ˌælsɪbˈaɪədiːz", "Plato": "plˈeɪtəʊ", "Horan": "hˈɒɹən",
    "Pericles": "pˈɛɹɪkliːz", "Clinias": "klˈɪnɪəs", "Xanthippus": "zænθˈɪpəs", "Gorgias": "ɡˈɔːdʒɪəs",
    "Meletus": "mˈɛlɪtəs", "Callias": "kˈælɪəs", "Zeno": "zˈiːnəʊ", "Pythodorus": "pˌɪθədˈɔːɹəs",
    "Isolochus": "aɪsˈɒləkəs", "Calliades": "kælˈaɪədiːz", "Artaxerxes": "ˌɑːtəzˈɜːksiːz",
    "Lacedaemonians": "lˌæsɪdɪmˈəʊnɪənz", "Lacedaemon": "lˌæsɪdˈiːmən", "Achaemenes": "əkˈiːmɪniːz",
    "Zopyrus": "zˈɒpɪɹəs", "Amestris": "əmˈɛstɹɪs", "Dinomache": "dˌaɪnəʊmˈɑːkiː", "Midias": "mˈɪdɪəs",
    "Peparethian": "pˌɛpəɹˈiːθɪən", "Ionians": "aɪˈəʊnɪənz", "Daedalus": "dˈiːdələs",
    "Hephaestus": "hɪfˈiːstəs", "Achilles": "əkˈɪliːz", "Ajax": "ˈeɪdʒæks", "Delphi": "dˈɛlfaɪ",
    "Cleinias": "klˈaɪnɪəs",
    "Cleitophon": "klˈaɪtəfɒn",
    "Heracleitus": "hˌɛɹəklˈaɪtəs",
    "Adeimantus": "ˌædɪmˈæntəs",
    "Hellenes": "hˈɛliːnz",
    "Hellas": "hˈɛləs",
    "Hellenic": "hɛlˈɛnɪk",
    "Hellene": "hˈɛliːn",
    "Cnosus": "nˈəʊsəs",
    "Cnosians": "nˈəʊsɪənz",
    "Cnosian": "nˈəʊsɪən",
    "Cronos": "kɹˈəʊnɒs",
    "Athene": "əθˈiːniː",
    "Pyriphlegethon": "pˌɪɹɪflˈɛɡɪθɒn",
    "Peloponnesus": "pˌɛləpənˈiːsəs",
    "Tyrrhenia": "tɪɹˈiːnɪə",
    "Zamolxis": "zəmˈɒlksɪs",
    "Lacedaemonian": "lˌæsɪdɪmˈəʊnɪən",
    "Jowett": "dʒˈəʊɪt",
}
US = {
    "Socrates": "sˈɑkɹətiz", "Alcibiades": "ˌælsəbˈaɪədiz", "Plato": "plˈeɪtoʊ", "Horan": "hˈɔɹən",
    "Pericles": "pˈɛɹəkliz", "Clinias": "klˈɪniəs", "Xanthippus": "zænθˈɪpəs", "Gorgias": "ɡˈɔɹdʒiəs",
    "Meletus": "mˈɛlətəs", "Callias": "kˈæliəs", "Zeno": "zˈinoʊ", "Pythodorus": "pˌɪθədˈɔɹəs",
    "Isolochus": "aɪsˈɑləkəs", "Calliades": "kælˈaɪədiz", "Artaxerxes": "ˌɑɹtəzˈɝksiz",
    "Lacedaemonians": "lˌæsədəmˈoʊniənz", "Lacedaemon": "lˌæsədˈimən", "Achaemenes": "əkˈimədiz",
    "Zopyrus": "zˈɑpəɹəs", "Amestris": "əmˈɛstɹɪs", "Dinomache": "dˌaɪnoʊmˈɑki", "Midias": "mˈɪdiəs",
    "Peparethian": "pˌɛpəɹˈiθiən", "Ionians": "aɪˈoʊniənz", "Daedalus": "dˈɛdələs",
    "Hephaestus": "həfˈɛstəs", "Achilles": "əkˈɪliz", "Ajax": "ˈeɪdʒæks", "Delphi": "dˈɛlfaɪ",
    "Cleinias": "klˈaɪniəs",
    "Cleitophon": "klˈaɪtəfɑn",
    "Heracleitus": "hˌɛɹəklˈaɪtəs",
    "Adeimantus": "ˌædəmˈæntəs",
    "Hellenes": "hˈɛlinz",
    "Hellas": "hˈɛləs",
    "Hellenic": "hɛlˈɛnɪk",
    "Hellene": "hˈɛlin",
    "Cnosus": "nˈoʊsəs",
    "Cnosians": "nˈoʊsiənz",
    "Cnosian": "nˈoʊsiən",
    "Cronos": "kɹˈoʊnɑs",
    "Athene": "əθˈini",
    "Pyriphlegethon": "pˌɪɹəflˈɛɡəθɑn",
    "Peloponnesus": "pˌɛləpənˈisəs",
    "Tyrrhenia": "tɪɹˈiniə",
    "Zamolxis": "zəmˈɑlksɪs",
    "Lacedaemonian": "lˌæsədəmˈoʊniən",
    "Jowett": "dʒˈoʊət",
}
LEX = {"gb": GB, "us": US}


def _poss(ipa):
    return ipa + ("" if ipa.endswith(("s", "z")) else "z")


def mark(text, accent):
    """Wrap known names in Kokoro's [word](/ipa/) syntax. Handles X's and X' possessives."""
    lex = LEX[accent]
    names = sorted(lex, key=len, reverse=True)
    pat = re.compile(r"\b(" + "|".join(map(re.escape, names)) + r")(['’]s?)?(?![\w'’])")

    def sub(m):
        w, p = m.group(1), m.group(2)
        ipa = lex[w]
        if p:
            return f"[{w}{p}](/{_poss(ipa)}/)"
        return f"[{w}](/{ipa}/)"
    return pat.sub(sub, text)
