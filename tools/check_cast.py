"""Check the cast against every script: every speaker cast; no two characters in one work share a voice;
reserved Socrates voices (george, santa, daniel, liam, eric) used by Socrates only. Exit 1 on a problem."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "engines"))
from script import load_cast, work_parts, ROOT  # noqa: E402

RESERVED = ("bm_george", "am_santa", "bm_daniel", "am_liam", "am_eric")
cast, bad = load_cast(), 0
ch = cast["characters"]
for k, c in ch.items():
    if k not in ("Socrates",) and any(v.startswith(RESERVED) for v, _ in c.get("kokoro", [])):
        print("RESERVED VOICE", k); bad += 1
import glob
for x in [x for f in sorted(glob.glob(os.path.join(ROOT, "scripts", "index*.json"))) for x in json.load(open(f))]:
    w, seen = x["key"], {}
    who = sorted({l["who"] for p in work_parts(w) for l in p["lines"]} - {"Narrator"})
    for s in who:
        c = ch.get(f"{w}:{s}") or ch.get(s)
        if c is None:
            print("UNCAST", w, s); bad += 1; continue
        sig = json.dumps([c["engine"], c.get("kokoro") or c.get("ref"), c.get("pitch", 0)])
        if sig in seen:
            print("SAME VOICE", w, s, "=", seen[sig]); bad += 1
        seen[sig] = s
print("problems:", bad); sys.exit(1 if bad else 0)
