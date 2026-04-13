#!/usr/bin/env python3
"""
Key & Peele enrichment script
- Fetches all episodes + metadata from TMDB
- Downloads episode stills and season posters
- Uses Anthropic API to identify sketches per episode and tag them
- Outputs kp_data.json ready to bake into the GVV hub

Usage:
    chmod +x enrich_kp.py
    ./enrich_kp.py

Or drag to terminal to run.

Requirements:
    pip install requests anthropic --break-system-packages
"""

import os, json, time, re, sys
import requests

# ── Config ────────────────────────────────────────────────────────────────────
TMDB_API_KEY   = "573382ec2121f69d6a89fce35293591a"
ANTHROPIC_KEY  = "YOUR_ANTHROPIC_KEY_HERE"   # replace or set env var ANTHROPIC_API_KEY
SERIES_ID      = 43082
TMDB_IMG_BASE  = "https://image.tmdb.org/t/p/w780"
TMDB_STILL_BASE= "https://image.tmdb.org/t/p/w780"

# Output paths (relative to script location)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR    = os.path.join(SCRIPT_DIR, "images", "kp")
OUTPUT     = os.path.join(SCRIPT_DIR, "kp_data.json")

os.makedirs(IMG_DIR, exist_ok=True)

# ── Sketch series vocabulary for AI tagging ───────────────────────────────────
SKETCH_SERIES = {
    "obama_luther":       "Obama & Luther — President Obama with his anger translator Luther",
    "substitute_teacher": "Substitute Teacher — Mr. Garvey butchers students' names (A-A-Ron, Jay-Quellin, etc.)",
    "east_west_bowl":     "East/West Bowl — college football player introductions with absurd names",
    "the_valets":         "The Valets — two valets from Berkshire Restaurant obsess over celebrities (Liam Neesons, etc.)",
    "wendell":            "Wendell — sad, neurotic consumer character",
    "meegan_andre":       "Meegan & André — toxic on-again off-again couple",
    "metta_world_news":   "Metta World News — NBA player Metta World Peace delivers bizarre news",
    "levi_cedric":        "Levi & Cedric — two inner-city friends, Levi constantly joins new trends",
    "black_republicans":  "Black Republicans — group of black men trying to recruit other Black voters to the GOP",
}

EPISODE_TAGS = [
    "celebrity_guest",   # notable celebrity appears
    "race_politics",     # pointed racial or political commentary
    "horror_parody",     # horror/thriller genre parody
    "sports_parody",     # sports parody
    "pop_culture",       # parodies a specific film, show, or cultural moment
]

# Format by season
LIVE_AUDIENCE_SEASONS = {1, 2, 3}   # had live audience + standup intros
CAR_CONVO_SEASONS     = {4, 5}      # car conversation intros, no audience

# ── Helpers ───────────────────────────────────────────────────────────────────
def tmdb_get(path, params=None):
    url = f"https://api.themoviedb.org/3{path}"
    p = {"api_key": TMDB_API_KEY, "language": "en-US"}
    if params:
        p.update(params)
    r = requests.get(url, params=p, timeout=15)
    r.raise_for_status()
    return r.json()

def download_image(url, dest):
    """Download image only if it doesn't already exist."""
    if os.path.exists(dest):
        return True
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        with open(dest, "wb") as f:
            f.write(r.content)
        return True
    except Exception as e:
        print(f"  ⚠ Could not download {url}: {e}")
        return False

def slug(s):
    return re.sub(r'[^a-z0-9]+', '_', s.lower()).strip('_')

# ── Anthropic sketch tagging ──────────────────────────────────────────────────
import anthropic as _anthropic

def get_anthropic_client():
    key = ANTHROPIC_KEY if ANTHROPIC_KEY != "YOUR_ANTHROPIC_KEY_HERE" else os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        print("ERROR: Set ANTHROPIC_KEY in script or ANTHROPIC_API_KEY env var")
        sys.exit(1)
    return _anthropic.Anthropic(api_key=key)

def tag_episode(client, season, episode, title, overview, tmdb_guests):
    """Use Claude to identify sketches in this episode and tag them."""

    series_desc = "\n".join(f"  - {k}: {v}" for k, v in SKETCH_SERIES.items())
    tag_desc    = ", ".join(EPISODE_TAGS)
    guest_str   = ", ".join(tmdb_guests[:10]) if tmdb_guests else "none listed"

    prompt = f"""You are helping build a TV archive for Key & Peele (Comedy Central, 2012-2015).

I need you to analyze this episode and return structured JSON data.

EPISODE: Season {season}, Episode {episode} — "{title}"
TMDB OVERVIEW: {overview or 'No overview available.'}
GUEST STARS (from TMDB): {guest_str}

YOUR TASKS:

1. SKETCHES: Identify the individual sketches in this episode. Key & Peele episodes typically contain 4-6 sketches. Use the overview and your knowledge of the show.
   For each sketch provide:
   - title: short name for the sketch (e.g. "Substitute Teacher", "Obama's Anger Translator", "Text Message Confusion")
   - series: the recurring series key if it belongs to one (see list below), or null if it's a standalone sketch
   - description: 1-2 sentence description of the sketch's premise

   RECURRING SERIES KEYS:
{series_desc}

2. EPISODE TAGS: From this list, apply any that fit: {tag_desc}
   - celebrity_guest: a notable celebrity appears (check guest stars)
   - race_politics: sketch has pointed racial or political commentary
   - horror_parody: parodies horror/thriller genre
   - sports_parody: parodies sports
   - pop_culture: parodies a specific film, show, or cultural moment

3. GUEST STARS: From the TMDB guest list, identify which are recognizable celebrities (not just background actors). Return their names as a clean list.

Respond ONLY with valid JSON in exactly this format, no markdown, no preamble:
{{
  "sketches": [
    {{"title": "Sketch Name", "series": "series_key_or_null", "description": "What happens in the sketch."}},
    ...
  ],
  "tags": ["tag1", "tag2"],
  "notable_guests": ["Name 1", "Name 2"]
}}"""

    try:
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = msg.content[0].text.strip()
        # Strip any accidental markdown fences
        raw = re.sub(r'^```json\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
        return json.loads(raw)
    except Exception as e:
        print(f"  ⚠ AI tagging failed for S{season:02d}E{episode:02d}: {e}")
        return {"sketches": [], "tags": [], "notable_guests": []}

# ── Main enrichment ───────────────────────────────────────────────────────────
def main():
    print("=== Key & Peele Enrichment ===\n")

    client = get_anthropic_client()

    # 1. Series metadata
    print("Fetching series metadata...")
    series = tmdb_get(f"/tv/{SERIES_ID}")
    series_data = {
        "title":       series["name"],
        "network":     series["networks"][0]["name"] if series.get("networks") else "Comedy Central",
        "years":       f"{series['first_air_date'][:4]}–{series['last_air_date'][:4]}",
        "seasons":     series["number_of_seasons"],
        "total_episodes": series["number_of_episodes"],
        "description": series["overview"],
        "hero":        "./images/kp/hero.jpg",
    }

    # Download series backdrop as hero
    if series.get("backdrop_path"):
        download_image(
            f"https://image.tmdb.org/t/p/w1280{series['backdrop_path']}",
            os.path.join(IMG_DIR, "hero.jpg")
        )

    # 2. Season metadata
    print("Fetching season metadata...")
    season_meta = {}
    for sn in range(1, 6):
        s = tmdb_get(f"/tv/{SERIES_ID}/season/{sn}")
        poster_file = f"season{sn}_poster.jpg"
        if s.get("poster_path"):
            download_image(
                f"{TMDB_IMG_BASE}{s['poster_path']}",
                os.path.join(IMG_DIR, poster_file)
            )
        backdrop_file = f"season{sn}_backdrop.jpg"
        if s.get("overview") and s.get("poster_path"):
            # Also try backdrop via series images endpoint
            pass

        format_label = "live_audience" if sn in LIVE_AUDIENCE_SEASONS else "car_conversation"
        format_desc  = "Live studio audience with standup intros" if sn in LIVE_AUDIENCE_SEASONS else "Car conversation cold opens, no studio audience"

        season_meta[str(sn)] = {
            "poster":      f"./images/kp/{poster_file}",
            "overview":    s.get("overview", ""),
            "air_date":    s.get("air_date", ""),
            "ep_count":    len(s.get("episodes", [])),
            "format":      format_label,
            "format_desc": format_desc,
        }
        print(f"  Season {sn}: {len(s.get('episodes', []))} episodes")

    # 3. Episodes
    print("\nFetching episodes and tagging sketches...\n")
    all_episodes = []

    for sn in range(1, 6):
        season_data = tmdb_get(f"/tv/{SERIES_ID}/season/{sn}")
        episodes    = season_data.get("episodes", [])

        for ep in episodes:
            ep_num   = ep["episode_number"]
            title    = ep.get("name", f"Episode {ep_num}")
            overview = ep.get("overview", "")
            air_date = ep.get("air_date", "")
            still_path = ep.get("still_path", "")

            # Guest stars from TMDB
            tmdb_guests = [g["name"] for g in ep.get("guest_stars", [])]

            ep_id = f"S{sn:02d}E{ep_num:02d}"
            print(f"  {ep_id} — {title}")

            # Download still
            still_file = f"{ep_id.lower()}_still.jpg"
            still_local = f"./images/kp/{still_file}"
            if still_path:
                download_image(
                    f"{TMDB_STILL_BASE}{still_path}",
                    os.path.join(IMG_DIR, still_file)
                )
            else:
                still_local = ""

            # AI tagging
            ai = tag_episode(client, sn, ep_num, title, overview, tmdb_guests)
            time.sleep(0.3)  # gentle rate limiting

            format_label = "live_audience" if sn in LIVE_AUDIENCE_SEASONS else "car_conversation"

            episode_obj = {
                "id":           ep_id,
                "season":       sn,
                "episode":      ep_num,
                "title":        title,
                "air_date":     air_date,
                "overview":     overview,
                "still":        still_local,
                "still_tmdb":   still_path,
                "sketches":     ai.get("sketches", []),
                "tags":         ai.get("tags", []),
                "notable_guests": ai.get("notable_guests", []),
                "tmdb_guests":  tmdb_guests,
                "format":       format_label,
            }

            all_episodes.append(episode_obj)
            print(f"    ✓ {len(ai.get('sketches', []))} sketches tagged, tags: {ai.get('tags', [])}")

    # 4. Assemble final JSON
    output = {
        "series":      series_data,
        "season_meta": season_meta,
        "sketch_series": SKETCH_SERIES,
        "episodes":    all_episodes,
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Done! {len(all_episodes)} episodes written to {OUTPUT}")
    print(f"✓ Images downloaded to {IMG_DIR}")
    print(f"\nNext: give kp_data.json and the images/kp/ folder to Claude to build the hub.")

if __name__ == "__main__":
    main()
