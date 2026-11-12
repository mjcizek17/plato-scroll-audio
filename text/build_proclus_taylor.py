"""Scripts for Taylor's Proclus, Theology of Plato and Commentary on the Timaeus (queue Q).
python text/build_proclus_taylor.py EXTRACT_DIR  — EXTRACT_DIR holds extract_author.py's proclus-theology.json / proclus-timaeus.json.
Re-parts them: the endnotes, Taylor's additional notes and the list of philosophers' names are not read (notes are never read);
Theology parts are named by book and chapter ("Book II, Chapters V–IX"); the Timaeus books are cut into parts of about
30,000 characters at paragraph boundaries ("Book II, Part 3")."""
import json, re, sys
SRC = sys.argv[1]; MAXC = 30000
ROMAN = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7}
def lines_of(k):
    d = json.load(open(f'{SRC}/{k}.json')); return d, [l for p in d['parts'] for l in p['lines']]
def write(d, parts, k):
    d['parts'] = [p for p in parts if any(l['kind'] != 'heading' for l in p['lines'])]
    out = []                                   # a scrap of a part (under 6,000 characters) joins the part before it, in the same book
    for p in d['parts']:
        n = sum(len(l['text']) for l in p['lines'])
        if out and n < 6000 and p['name'].split(',')[0] == out[-1]['name'].split(',')[0]:
            prev = out[-1]; prev['lines'] += [l for l in p['lines'] if not (l['kind'] == 'heading' and l['text'] == p['name'])]
            m1 = re.search(r'Chapters? ([IVXLC]+)', prev['name']); m2 = re.search(r'([IVXLC]+)$', p['name'])
            if m1 and m2 and 'Chapter' in p['name']: prev['name'] = re.sub(r'Chapters? .*$', f'Chapters {m1.group(1)}–{m2.group(1)}', prev['name'])
        else: out.append(p)
    d['parts'] = out
    json.dump(d, open(f'scripts/{k}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(k, len(d['parts']), 'parts', sum(len(l['text']) for p in d['parts'] for l in p['lines']), 'chars')
def skip(t): return re.match(r'^(endnotes|additional notes by the translator|names of the philosophers)', t.strip(), re.I)
# Theology
d, L = lines_of('proclus-theology'); parts = []; cur = None; book = None; dropping = False; first = last = None
def close():
    if cur and cur['lines']:
        if book and first: cur['name'] = f'Book {book}, Chapter{"s" if first != last else ""} {first}{"–" + last if first != last else ""}'
        parts.append(cur)
for l in L:
    t = l['text']
    if l['kind'] == 'heading':
        if skip(t): dropping = True; continue
        m = re.match(r'^(?:Book ([IVX]+)|On the Theology of Plato, a Seventh Book)', t, re.I)
        if m or re.match(r'^Introduction', t, re.I):
            dropping = False; close(); book = (m.group(1).upper() if m and m.group(1) else ('VII' if m else None))
            cur = {'name': t if not m else f'Book {book}', 'lines': [l]}; first = last = None; continue
        c = re.match(r'^Chapter ([IVXLC]+)', t, re.I)
        if c and not dropping:
            n = sum(len(x['text']) for x in cur['lines']) if cur else 0
            if cur and n > MAXC * 0.7 and first: close(); cur = {'name': '', 'lines': []}; first = None
            first = first or c.group(1).upper(); last = c.group(1).upper()
    if dropping: continue
    if cur is None: cur = {'name': 'Introduction', 'lines': []}
    cur['lines'].append(l)
close(); write(d, parts, 'proclus-theology')
# Timaeus
d, L = lines_of('proclus-timaeus'); parts = []; cur = None; book = None; dropping = False; k = 0
for l in L:
    t = l['text']
    if l['kind'] == 'heading':
        if skip(t): dropping = True; continue
        m = re.match(r'^Book ([IVX]+)', t, re.I)
        if m or re.match(r'^Introduction', t, re.I):
            dropping = False
            if cur: parts.append(cur)
            book = m.group(1).upper() if m else None; k = 1
            cur = {'name': f'Book {book}, Part 1' if book else t, 'lines': [l]}; continue
    if dropping: continue
    if book and cur and sum(len(x['text']) for x in cur['lines']) > MAXC and l['kind'] != 'heading':
        parts.append(cur); k += 1; cur = {'name': f'Book {book}, Part {k}', 'lines': [{**l, 'kind': 'heading', 'text': f'Book {book}, Part {k}'}, l]}
        continue
    cur['lines'].append(l)
if cur: parts.append(cur)
write(d, parts, 'proclus-timaeus')
