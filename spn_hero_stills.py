#!/usr/bin/env python3
"""
spn_hero_stills.py
==================
Pulls specific episode stills for Sam and Dean hero cards.

  Sam:  S14E02 — Gods and Monsters
  Dean: S09E18 — Meta Fiction

Saves them as:
  images/supernatural/hero_sam.jpg
  images/supernatural/hero_dean.jpg

Run from the TV Vault folder:
    python3 spn_hero_stills.py
"""

import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("Run: pip3 install requests --break-system-packages")
    raise SystemExit

TMDB_KEY = "573382ec2121f69d6a89fce35293591a"
IMG_DIR  = Path("images/supernatural")
IMG_DIR.mkdir(parents=True, exist_ok=True)

TARGETS = [
    ("hero_sam",  14, 2,  "Gods and Monsters — Sam close-up"),
    ("hero_dean",  9, 18, "Meta Fiction — Dean close-up"),
]

def tmdb_get(path):
    url = f"https://api.themoviedb.org/3{path}"
    r = requests.get(url, params={"api_key": TMDB_KEY, "language": "en-US"}, timeout=15)
    r.raise_for_status()
    time.sleep(0.3)
    return r.json()

def download(url, dest, label):
    print(f"  Downloading {label}...")
    r = requests.get(url, timeout=30)
    if len(r.content) < 5000:
        print(f"  ✗ File too small — something went wrong")
        return False
    Path(dest).write_bytes(r.content)
    print(f"  ✓ Saved → {dest}")
    return True

print("=" * 52)
print("  Supernatural — Hero Card Stills")
print("=" * 52)

for filename, season, episode, label in TARGETS:
    dest = IMG_DIR / f"{filename}.jpg"
    print(f"\n{label} (S{season:02d}E{episode:02d})")
    try:
        ep = tmdb_get(f"/tv/1622/season/{season}/episode/{episode}")
        still = ep.get("still_path")
        if not still:
            print(f"  ✗ No still found on TMDB for S{season:02d}E{episode:02d}")
            continue
        url = f"https://image.tmdb.org/t/p/original{still}"
        download(url, dest, f"{filename}.jpg")
    except Exception as e:
        print(f"  ✗ Error: {e}")

print(f"""
{'='*52}
Done. Drop these into images/supernatural/ if not
already there, then hard-refresh (Cmd+Shift+R).

  hero_sam.jpg  → Sam hero card background
  hero_dean.jpg → Dean hero card background
{'='*52}
""")
