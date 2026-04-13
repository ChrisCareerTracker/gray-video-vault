#!/usr/bin/env python3
"""
supernatural_enrich.py
======================
Builds supernatural_data.json in the GVV flat standard and downloads
all episode stills + season posters for the Supernatural hub.

TMDB Series ID: 1622
Output: supernatural_data.json
Images: images/supernatural/  (episode stills + season posters + hero)

Run from the TV Vault folder:
    python3 supernatural_enrich.py

Requires: requests  (pip3 install requests --break-system-packages)
"""

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: 'requests' not installed.")
    print("Run: pip3 install requests --break-system-packages")
    sys.exit(1)

# ── CONFIG ─────────────────────────────────────────────────────────────────────
TMDB_API_KEY = "573382ec2121f69d6a89fce35293591a"
SERIES_ID    = 1622
OUT_JSON     = "supernatural_data.json"
IMG_DIR      = Path("images/supernatural")
TMDB_IMG     = "https://image.tmdb.org/t/p/w500"
TMDB_ORIG    = "https://image.tmdb.org/t/p/original"
DELAY        = 0.25   # seconds between TMDB requests to be polite

# Season era metadata — drives taglines and band styling in the hub
ERA_META = {
    1:  {"era": "kripke",     "tagline": "Saving people, hunting things. The family business."},
    2:  {"era": "kripke",     "tagline": "Every family has its demons."},
    3:  {"era": "kripke",     "tagline": "Dean's deal. Sixty-six seals. One year left."},
    4:  {"era": "kripke",     "tagline": "The angels have arrived — and that's not good news."},
    5:  {"era": "kripke",     "tagline": "The Apocalypse. The endgame Kripke always planned."},
    6:  {"era": "post-kripke","tagline": "Soulless Sam. Purgatory on the horizon."},
    7:  {"era": "post-kripke","tagline": "The Leviathans rise. Dick Roman's master plan."},
    8:  {"era": "carver",     "tagline": "Purgatory, Trials, and the Men of Letters."},
    9:  {"era": "carver",     "tagline": "Gadreel. The Mark of Cain begins."},
    10: {"era": "carver",     "tagline": "The Mark consumes. Dean becomes the Darkness."},
    11: {"era": "carver",     "tagline": "The Darkness unleashed. God steps out of the shadows."},
    12: {"era": "dabb",       "tagline": "The British Men of Letters. Mary Winchester returns."},
    13: {"era": "dabb",       "tagline": "Apocalypse World. A Nephilim called Jack."},
    14: {"era": "dabb",       "tagline": "Michael possesses Dean. A new God rises."},
    15: {"era": "dabb",       "tagline": "The final road. Chuck writes the ending — or tries to."},
}

# Filter tags per episode — hand-curated list of notable episodes
# Format: "S##E##": ["TAG1", "TAG2"]
# Tags: MYTHOLOGY · MONSTER_OF_THE_WEEK · FAN_FAVORITE · HOLIDAY · MUSICAL_META
EPISODE_TAGS = {
    # S1 — Kripke era foundations
    "S01E01": ["MYTHOLOGY", "FAN_FAVORITE"],
    "S01E08": ["MONSTER_OF_THE_WEEK"],
    "S01E12": ["MYTHOLOGY"],
    "S01E22": ["MYTHOLOGY", "FAN_FAVORITE"],
    # S2
    "S02E01": ["MYTHOLOGY"],
    "S02E02": ["MONSTER_OF_THE_WEEK", "FAN_FAVORITE"],
    "S02E11": ["HOLIDAY"],                              # Playthings (creepy Xmas-adjacent)
    "S02E15": ["MUSICAL_META"],                         # Tall Tales
    "S02E19": ["MYTHOLOGY"],
    "S02E20": ["MYTHOLOGY", "FAN_FAVORITE"],
    "S02E21": ["MYTHOLOGY"],
    "S02E22": ["MYTHOLOGY", "FAN_FAVORITE"],
    # S3
    "S03E03": ["MONSTER_OF_THE_WEEK", "FAN_FAVORITE"],  # Bad Day at Black Rock
    "S03E08": ["HOLIDAY", "FAN_FAVORITE"],              # A Very Supernatural Christmas
    "S03E11": ["MUSICAL_META", "FAN_FAVORITE"],         # Mystery Spot
    "S03E16": ["MYTHOLOGY", "FAN_FAVORITE"],
    # S4
    "S04E01": ["MYTHOLOGY", "FAN_FAVORITE"],
    "S04E06": ["MUSICAL_META"],                         # Yellow Fever
    "S04E18": ["MONSTER_OF_THE_WEEK", "FAN_FAVORITE"],  # The Monster at the End of This Book
    "S04E21": ["MYTHOLOGY"],
    "S04E22": ["MYTHOLOGY", "FAN_FAVORITE"],
    # S5
    "S05E01": ["MYTHOLOGY", "FAN_FAVORITE"],
    "S05E04": ["FAN_FAVORITE"],                         # The End
    "S05E08": ["HOLIDAY", "FAN_FAVORITE"],              # Changing Channels
    "S05E09": ["MUSICAL_META", "FAN_FAVORITE"],
    "S05E14": ["MONSTER_OF_THE_WEEK"],                  # My Bloody Valentine
    "S05E22": ["MYTHOLOGY", "FAN_FAVORITE"],
    # S6
    "S06E15": ["MUSICAL_META"],                         # The French Mistake
    "S06E20": ["MYTHOLOGY"],
    "S06E22": ["MYTHOLOGY"],
    # S7
    "S07E02": ["MYTHOLOGY"],
    "S07E05": ["MONSTER_OF_THE_WEEK", "FAN_FAVORITE"],  # Shut Up, Dr. Phil
    "S07E23": ["MYTHOLOGY"],
    # S8
    "S08E08": ["HOLIDAY", "FAN_FAVORITE"],
    "S08E11": ["MUSICAL_META", "FAN_FAVORITE"],         # LARP and the Real Girl
    "S08E23": ["MYTHOLOGY", "FAN_FAVORITE"],
    # S9
    "S09E07": ["HOLIDAY"],
    "S09E18": ["MYTHOLOGY"],
    "S09E23": ["MYTHOLOGY", "FAN_FAVORITE"],
    # S10
    "S10E05": ["MUSICAL_META", "FAN_FAVORITE"],         # Fan Fiction — THE Musical episode
    "S10E12": ["FAN_FAVORITE"],
    "S10E23": ["MYTHOLOGY", "FAN_FAVORITE"],
    # S11
    "S11E04": ["HOLIDAY"],
    "S11E08": ["MYTHOLOGY"],
    "S11E23": ["MYTHOLOGY", "FAN_FAVORITE"],
    # S12
    "S12E11": ["MUSICAL_META", "FAN_FAVORITE"],         # Regarding Dean
    "S12E22": ["MYTHOLOGY"],
    "S12E23": ["MYTHOLOGY", "FAN_FAVORITE"],
    # S13
    "S13E06": ["MONSTER_OF_THE_WEEK", "FAN_FAVORITE"],  # Tombstone
    "S13E16": ["MUSICAL_META", "FAN_FAVORITE"],         # Scoobynatural
    "S13E22": ["MYTHOLOGY"],
    "S13E23": ["MYTHOLOGY"],
    # S14
    "S14E07": ["HOLIDAY", "FAN_FAVORITE"],
    "S14E20": ["MYTHOLOGY", "FAN_FAVORITE"],
    # S15
    "S15E01": ["MYTHOLOGY"],
    "S15E13": ["FAN_FAVORITE"],                         # Destiny's Child
    "S15E18": ["FAN_FAVORITE"],                         # Despair
    "S15E19": ["FAN_FAVORITE"],                         # Inherit the Earth
    "S15E20": ["MYTHOLOGY", "FAN_FAVORITE"],            # Carry On
}


# ── HELPERS ────────────────────────────────────────────────────────────────────
def tmdb_get(path, params=None):
    """GET from TMDB API. Returns parsed JSON or raises on error."""
    url = f"https://api.themoviedb.org/3{path}"
    p = {"api_key": TMDB_API_KEY, "language": "en-US"}
    if params:
        p.update(params)
    r = requests.get(url, params=p, timeout=15)
    r.raise_for_status()
    time.sleep(DELAY)
    return r.json()


def download_image(url, dest: Path, label=""):
    """Download an image from url to dest. Skip if dest exists and is >1KB."""
    if dest.exists() and dest.stat().st_size > 1024:
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = resp.read()
        if len(data) < 1024:
            print(f"  ⚠ Tiny file, skipping: {label}")
            return False
        dest.write_bytes(data)
        return True
    except Exception as e:
        print(f"  ✗ Download failed for {label}: {e}")
        return False


def safe_filename(s):
    """Strip characters that break Netlify / GitHub Pages."""
    return s.replace(" ", "_").replace("'", "").replace('"', "").replace(".", "").replace("/", "-")


# ── MAIN ───────────────────────────────────────────────────────────────────────
def main():
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  Supernatural Enrichment Script")
    print("  TMDB Series ID: 1622")
    print("=" * 60)

    # ── 1. Series details ──────────────────────────────────────────────────────
    print("\n[1/4] Fetching series metadata …")
    series = tmdb_get(f"/tv/{SERIES_ID}")
    total_seasons = series["number_of_seasons"]
    total_episodes = series["number_of_episodes"]
    print(f"  Found {total_seasons} seasons, {total_episodes} episodes")

    # ── 2. Season + episode loop ───────────────────────────────────────────────
    print(f"\n[2/4] Fetching all seasons …")

    season_meta = {}
    episodes_flat = []

    for s_num in range(1, total_seasons + 1):
        print(f"  Season {s_num} …", end=" ", flush=True)
        sd = tmdb_get(f"/tv/{SERIES_ID}/season/{s_num}")

        # Season poster
        poster_path = sd.get("poster_path") or series.get("poster_path", "")
        poster_url  = f"{TMDB_IMG}{poster_path}" if poster_path else ""
        poster_file = f"images/supernatural/season_{s_num:02d}_poster.jpg"

        era_info = ERA_META.get(s_num, {"era": "dabb", "tagline": ""})

        # Parse air year from first episode
        raw_date = sd.get("air_date") or ""
        air_year = raw_date[:4] if raw_date else str(2004 + s_num)

        season_meta[str(s_num)] = {
            "year": air_year,
            "network": "The CW" if s_num >= 2 else "The WB",
            "era": era_info["era"],
            "tagline": era_info["tagline"],
            "poster": f"./{poster_file}",
            "episode_count": len(sd.get("episodes", [])),
        }

        # Download season poster
        if poster_url:
            download_image(poster_url, Path(poster_file),
                           label=f"Season {s_num} poster")

        # Process episodes
        eps = sd.get("episodes", [])
        for ep in eps:
            e_num = ep.get("episode_number", 0)
            tag_key = f"S{s_num:02d}E{e_num:02d}"

            # Still image
            still_path = ep.get("still_path") or ""
            still_url  = f"{TMDB_IMG}{still_path}" if still_path else ""
            still_file = f"images/supernatural/s{s_num:02d}e{e_num:02d}.jpg"

            if still_url:
                download_image(still_url, Path(still_file),
                               label=f"S{s_num:02d}E{e_num:02d}")

            # Guest stars — from ep credits if available
            guests = []
            if ep.get("guest_stars"):
                guests = [g["name"] for g in ep["guest_stars"][:6]]

            episodes_flat.append({
                "season":    s_num,
                "episode":   e_num,
                "title":     ep.get("name", ""),
                "air_date":  ep.get("air_date", ""),
                "overview":  ep.get("overview", ""),
                "still":     f"./{still_file}" if still_url else "",
                "rating":    round(ep.get("vote_average", 0.0), 1),
                "guests":    guests,
                "tags":      EPISODE_TAGS.get(tag_key, []),
            })

        print(f"{len(eps)} episodes")

    # ── 3. Hero / backdrop images ──────────────────────────────────────────────
    print("\n[3/4] Downloading hero + backdrop images …")

    # Use backdrop for hero banner and series backdrop
    backdrops = tmdb_get(f"/tv/{SERIES_ID}/images", {"include_image_language": "en,null"})
    backdrop_list = backdrops.get("backdrops", [])
    if backdrop_list:
        best_backdrop = sorted(backdrop_list, key=lambda x: x.get("vote_average", 0), reverse=True)[0]
        backdrop_url = f"{TMDB_ORIG}{best_backdrop['file_path']}"
        download_image(backdrop_url, Path("images/supernatural/hero.jpg"), label="hero")
        download_image(backdrop_url, Path("images/supernatural/backdrop.jpg"), label="backdrop")
        print("  ✓ hero.jpg and backdrop.jpg saved")
    else:
        print("  ⚠ No backdrops found — using existing show poster")

    # Season poster montage images — download higher-res versions too
    # (already done per-season above, this is just a status note)
    print("  ✓ Season posters downloaded per-season above")

    # ── 4. Build and write JSON ────────────────────────────────────────────────
    print("\n[4/4] Writing supernatural_data.json …")

    output = {
        "series": {
            "title":   "Supernatural",
            "network": "The CW",
            "years":   "2005-2020",
            "tmdb_id": SERIES_ID,
            "seasons": total_seasons,
            "hero":    "./images/supernatural/hero.jpg",
            "backdrop":"./images/supernatural/backdrop.jpg",
            "poster":  "./images/shows/Supernatural_poster.jpg",
            "description": (
                "Two brothers follow their father's footsteps as hunters, "
                "fighting evil supernatural beings of many kinds including "
                "monsters, demons, and gods that roam the earth."
            ),
        },
        "season_meta":  season_meta,
        "episodes":     episodes_flat,
    }

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    ep_count = len(episodes_flat)
    print(f"  ✓ {OUT_JSON} written — {ep_count} episodes across {total_seasons} seasons")

    # ── Summary ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  DONE")
    print(f"  JSON:   {OUT_JSON}")
    print(f"  Images: {IMG_DIR}/")
    print(f"  Episodes enriched: {ep_count}")

    # Quick tag audit
    tagged = [e for e in episodes_flat if e["tags"]]
    print(f"  Tagged episodes: {len(tagged)}")
    print("=" * 60)

    # Verify episode count matches known total
    if ep_count != 327:
        print(f"\n  ⚠ WARNING: Expected 327 episodes, got {ep_count}.")
        print("    TMDB may have a slightly different count (specials, etc).")
        print("    Review the output JSON before building the hub.")
    else:
        print(f"\n  ✓ Episode count confirmed: {ep_count}")


if __name__ == "__main__":
    main()
