#!/usr/bin/env python3
"""
spn_pull_images.py
==================
Pulls actor profile images from TMDB for all Supernatural characters
and saves them as char_[id].jpg in images/supernatural/.
Also pulls targeted episode stills for Sam and Dean hero cards.

Run from the TV Vault folder:
    python3 spn_pull_images.py

Requires: requests  (pip3 install requests --break-system-packages)
"""

import json, os, time, sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Run: pip3 install requests --break-system-packages")
    sys.exit(1)

TMDB_KEY  = "573382ec2121f69d6a89fce35293591a"
TMDB_IMG  = "https://image.tmdb.org/t/p/w300"
IMG_DIR   = Path("images/supernatural")
DELAY     = 0.25

IMG_DIR.mkdir(parents=True, exist_ok=True)

# ── Character → actor name mapping ───────────────────────────────
CHARACTERS = [
    ("sam",      "Sam Winchester",   "Jared Padalecki"),
    ("dean",     "Dean Winchester",  "Jensen Ackles"),
    ("castiel",  "Castiel",          "Misha Collins"),
    ("bobby",    "Bobby Singer",     "Jim Beaver"),
    ("crowley",  "Crowley",          "Mark Sheppard"),
    ("jack",     "Jack Kline",       "Alexander Calvert"),
    ("mary",     "Mary Winchester",  "Samantha Smith"),
    ("john",     "John Winchester",  "Jeffrey Dean Morgan"),
    ("lucifer",  "Lucifer",          "Mark Pellegrino"),
    ("chuck",    "Chuck / God",      "Rob Benedict"),
    ("rowena",   "Rowena",           "Ruth Connell"),
    ("jody",     "Jody Mills",       "Kim Rhodes"),
    ("charlie",  "Charlie Bradbury", "Felicia Day"),
    ("donna",    "Donna Hanscum",    "Briana Buckmaster"),
    ("kevin",    "Kevin Tran",       "Osric Chau"),
    ("garth",    "Garth",            "DJ Qualls"),
    ("meg",      "Meg",              "Rachel Miner"),
    ("ruby",     "Ruby",             "Genevieve Cortese"),
    ("azazel",   "Azazel",           "Fredric Lehne"),
    ("abaddon",  "Abaddon",          "Alaina Huffman"),
    ("death",    "Death",            "Julian Richings"),
    ("amara",    "The Darkness",     "Emily Swallows"),
    ("michael",  "Michael",          "Matthew G. Taylor"),
    ("cain",     "Cain",             "Timothy Omundson"),
    ("metatron", "Metatron",         "Curtis Armstrong"),
    ("bela",     "Bela Talbot",      "Lauren Cohan"),
    ("dick",     "Dick Roman",       "James Patrick Stuart"),
]

# ── Hero card episode stills ──────────────────────────────────────
# Sam: S08E23 Sacrifice — strong Sam close-up, emotional finale
# Dean: S05E04 The End — iconic Dean-centric episode
HERO_STILLS = [
    ("hero_sam",  8, 23),
    ("hero_dean", 5,  4),
]

def tmdb_get(path, params=None):
    url = f"https://api.themoviedb.org/3{path}"
    p = {"api_key": TMDB_KEY, "language": "en-US"}
    if params: p.update(params)
    r = requests.get(url, params=p, timeout=15)
    r.raise_for_status()
    time.sleep(DELAY)
    return r.json()

def download(url, dest, label=""):
    dest = Path(dest)
    if dest.exists() and dest.stat().st_size > 2000:
        print(f"  → skip (exists): {dest.name}")
        return True
    try:
        r = requests.get(url, timeout=20)
        if len(r.content) < 2000:
            print(f"  ✗ too small: {label}")
            return False
        dest.write_bytes(r.content)
        print(f"  ✓ {dest.name}")
        return True
    except Exception as e:
        print(f"  ✗ {label}: {e}")
        return False

# ── 1. Actor headshots ────────────────────────────────────────────
print("=" * 56)
print("  Supernatural — Actor Image Pull")
print("=" * 56)
print(f"\n[1/2] Pulling {len(CHARACTERS)} actor headshots from TMDB...\n")

ok = 0
fail = 0
for char_id, char_name, actor_name in CHARACTERS:
    dest = IMG_DIR / f"char_{char_id}.jpg"
    print(f"  {char_name} ({actor_name})")
    try:
        data = tmdb_get("/search/person", {"query": actor_name})
        results = data.get("results", [])
        if not results:
            print(f"    ✗ No TMDB result for {actor_name}")
            fail += 1
            continue
        # Pick best result — prefer exact name match
        person = results[0]
        for r in results:
            if r.get("name","").lower() == actor_name.lower():
                person = r
                break
        profile = person.get("profile_path")
        if not profile:
            print(f"    ✗ No profile image for {actor_name}")
            fail += 1
            continue
        img_url = f"{TMDB_IMG}{profile}"
        if download(img_url, dest, actor_name):
            ok += 1
        else:
            fail += 1
    except Exception as e:
        print(f"    ✗ Error: {e}")
        fail += 1

# ── 2. Hero card stills ───────────────────────────────────────────
print(f"\n[2/2] Pulling hero card stills for Sam & Dean...\n")

SERIES_ID = 1622
for filename, season, episode in HERO_STILLS:
    dest = IMG_DIR / f"{filename}.jpg"
    print(f"  {filename} (S{season:02d}E{episode:02d})")
    try:
        ep_data = tmdb_get(f"/tv/{SERIES_ID}/season/{season}/episode/{episode}")
        still = ep_data.get("still_path")
        if still:
            # Use original size for hero cards
            url = f"https://image.tmdb.org/t/p/original{still}"
            download(url, dest, filename)
        else:
            print(f"    ✗ No still for S{season:02d}E{episode:02d}")
    except Exception as e:
        print(f"    ✗ {e}")

print(f"\n{'='*56}")
print(f"  Done — {ok} actors downloaded, {fail} failed")
print(f"  Images saved to: {IMG_DIR}/")
print(f"{'='*56}")
print("""
To swap any image out later, just save your replacement as
the same filename and drop it into images/supernatural/.
No code changes needed.

Sam hero card:  images/supernatural/hero_sam.jpg
Dean hero card: images/supernatural/hero_dean.jpg
""")
