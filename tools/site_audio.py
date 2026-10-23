"""Build the site's audio folder and the reader's built-in catalog from the published releases.
Usage: python tools/site_audio.py OUT_SITE_DIR [--js reader/audio-data.js] [--tags audio-v1 aristotle-v1 neoplatonists-v1 julian-v1 hermetica-v1 classics-v1 jowett-v1]
Writes OUT_SITE_DIR/audio/catalog.json and OUT_SITE_DIR/audio/<part>.timing.json for every MP3 on the releases.
catalog.json: {"works": {key: [{name, label, author, first, last, minutes, mp3: [url]}...]}}
  first/last = the entry range the part covers (for tap-to-seek and choosing the part on screen).
The MP3s stay on GitHub (streamed from releases/download/<tag>/<file>); only the small timing files go to the site.
Needs the gh CLI (authenticated) for the release listing and downloads."""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "mjcizek17/plato-scroll-audio"
sys.path.insert(0, os.path.join(ROOT, "engines"))


def gh(path, raw=False):
    args = ["gh", "api", path] + (["-H", "Accept: application/octet-stream"] if raw else [])
    out = subprocess.run(args, capture_output=True, check=True).stdout
    return out if raw else json.loads(out)


def main(out, js=None, tags=("audio-v1", "aristotle-v1", "neoplatonists-v1", "julian-v1", "hermetica-v1", "classics-v1", "jowett-v1")):
    adir = os.path.join(out, "audio"); os.makedirs(adir, exist_ok=True)
    works = {}
    idp = os.path.join(ROOT, ".cache", "timing-ids.json"); os.makedirs(os.path.dirname(idp), exist_ok=True)
    ids = json.load(open(idp)) if os.path.exists(idp) else {}
    for tag in tags:
        try:
            rel = gh(f"repos/{REPO}/releases/tags/{tag}")
        except subprocess.CalledProcessError:
            print("no release", tag); continue
        assets = {a["name"]: a for a in rel["assets"]}
        for name in sorted(assets):
            m = re.match(r"(.+)-p(\d+)\.mp3$", name)
            if not m or (m.group(0)[:-4] + ".timing.json") not in assets:
                continue
            key, part, stem = m.group(1), int(m.group(2)), name[:-4]
            tpath = os.path.join(adir, stem + ".timing.json")
            ta = assets[stem + ".timing.json"]
            if not os.path.exists(tpath) or os.path.getsize(tpath) != ta["size"] or ids.get(stem) != ta["id"]:
                open(tpath, "wb").write(gh(f"repos/{REPO}/releases/assets/{ta['id']}", raw=True)); ids[stem] = ta["id"]
            t = json.load(open(tpath))
            ents = [int(e) for e in list(t.get("entries", {})) + list(t.get("words", {}))]
            sp = os.path.join(ROOT, "scripts", key + ".json")
            s = json.load(open(sp)) if os.path.exists(sp) else {"title": key, "parts": []}
            title, author = s["title"], s.get("author", "Plato")
            tr = s.get("translator", "David Horan") if author == "Plato" else ""   # Plato has two recorded translations
            label = title
            if len(s["parts"]) > 1 and part <= len(s["parts"]):
                label = f"{title} — {s['parts'][part - 1]['name']}"
            last_w = max((v[-1] for v in t.get("words", {}).values() if v), default=0) / 100
            works.setdefault(key, []).append({
                "name": stem, "label": label, "author": author, "part": part, **({"tr": tr} if tr else {}),
                "first": min(ents) if ents else 0, "last": max(ents) if ents else 0,
                "minutes": round(last_w / 60, 1),
                # bytes: the offline-save size; v: the MP3's asset id, which changes when a recording is replaced,
                # so a copy saved for offline listening can tell it is out of date
                "bytes": assets[name]["size"], "v": assets[name]["id"],
                "mp3": [f"https://github.com/{REPO}/releases/download/{tag}/{name}"]})
    for k in works:
        works[k].sort(key=lambda p: p["part"])
        for p in works[k]:
            p.pop("part")
    cat = {"works": works}
    json.dump(ids, open(idp, "w"))
    json.dump(cat, open(os.path.join(adir, "catalog.json"), "w"), ensure_ascii=False, separators=(",", ":"))
    if js:
        open(js, "w").write("/* 5.20: built-in catalog of recorded works (tools/site_audio.py in plato-scroll-audio). "
                            "The reader refreshes it from audio/catalog.json on the site. */\nwindow.HV_AUDIO = "
                            + json.dumps(cat, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print(len(works), "works,", sum(len(v) for v in works.values()), "parts")


if __name__ == "__main__":
    a = sys.argv[1:]
    js = a[a.index("--js") + 1] if "--js" in a else None
    tags = a[a.index("--tags") + 1:] if "--tags" in a else ("audio-v1", "aristotle-v1", "neoplatonists-v1", "julian-v1", "hermetica-v1", "classics-v1", "jowett-v1")
    main(a[0], js, tags)
