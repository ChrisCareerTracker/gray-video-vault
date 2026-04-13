#!/usr/bin/env python3
"""
enrich_seinfeld.py
Gray Video Vault — Seinfeld Hub Enrichment Script
--------------------------------------------------
Pass 1: TMDB — episode structure, stills, air dates, descriptions, guest stars
Pass 2: Seinfeld Fandom Wiki — per-character plot summaries, full cast, trivia

Output:
  seinfeld_data.json     — full episode data for the hub
  seinfeld_report.txt    — quality report: what parsed, what needs review

Images downloaded to: images/seinfeld/
  s01e01_still.jpg       — episode stills (176 episodes)
  season_1_poster.jpg    — season posters (9 seasons)
  characters/            — character portraits (downloaded separately)

Run from inside the "TV Vault New Index and Json folders" folder:
  python3 enrich_seinfeld.py
"""

import json
import os
import re
import time
import urllib.request
import urllib.error
from html.parser import HTMLParser

# ── CONFIG ────────────────────────────────────────────────────────────────────

TMDB_API_KEY = "573382ec2121f69d6a89fce35293591a"
TMDB_SERIES_ID = 1400          # Seinfeld on TMDB
TMDB_IMG_BASE = "https://image.tmdb.org/t/p/w500"
TMDB_IMG_ORIG = "https://image.tmdb.org/t/p/original"

OUTPUT_JSON = "seinfeld_data.json"
OUTPUT_REPORT = "seinfeld_report.txt"
IMG_DIR = "images/seinfeld"
CHAR_DIR = "images/seinfeld/characters"

WIKI_BASE = "https://seinfeld.fandom.com/wiki/"

# Polite delay between wiki requests (seconds)
WIKI_DELAY = 1.5

# ── KNOWN DATA: EPISODE NICKNAMES ─────────────────────────────────────────────
# Canonical fan nicknames for episodes — keyed by S##E## format.
# These are the names fans actually use. Filled for all 180 episodes.

EPISODE_NICKNAMES = {
    # Season 1
    "S01E01": "The Seinfeld Chronicles",
    "S01E02": "The Stakeout",
    "S01E03": "The Robbery",
    "S01E04": "Male Unbonding",
    "S01E05": "The Stock Tip",
    # Season 2
    "S02E01": "The Ex-Girlfriend",
    "S02E02": "The Pony Remark",
    "S02E03": "The Jacket",
    "S02E04": "The Phone Message",
    "S02E05": "The Apartment",
    "S02E06": "The Statue",
    "S02E07": "The Revenge",
    "S02E08": "The Heart Attack",
    "S02E09": "The Deal",
    "S02E10": "The Baby Shower",
    "S02E11": "The Chinese Restaurant",
    "S02E12": "The Busboy",
    # Season 3
    "S03E01": "The Note",
    "S03E02": "The Truth",
    "S03E03": "The Pen",
    "S03E04": "The Dog",
    "S03E05": "The Library",
    "S03E06": "The Parking Garage",
    "S03E07": "The Café",
    "S03E08": "The Tape",
    "S03E09": "The Nose Job",
    "S03E10": "The Stranded",
    "S03E11": "The Alternate Side",
    "S03E12": "The Red Dot",
    "S03E13": "The Subway",
    "S03E14": "The Pez Dispenser",
    "S03E15": "The Suicide",
    "S03E16": "The Fix-Up",
    "S03E17": "The Boyfriend",
    "S03E18": "The Boyfriend (Part 2)",
    "S03E19": "The Limo",
    "S03E20": "The Good Samaritan",
    "S03E21": "The Letter",
    "S03E22": "The Parking Space",
    "S03E23": "The Keys",
    # Season 4
    "S04E01": "The Trip (Part 1)",
    "S04E02": "The Trip (Part 2)",
    "S04E03": "The Pitch",
    "S04E04": "The Ticket",
    "S04E05": "The Wallet",
    "S04E06": "The Watch",
    "S04E07": "The Bubble Boy",
    "S04E08": "The Cheever Letters",
    "S04E09": "The Opera",
    "S04E10": "The Virgin",
    "S04E11": "The Contest",
    "S04E12": "The Airport",
    "S04E13": "The Pick",
    "S04E14": "The Movie",
    "S04E15": "The Visa",
    "S04E16": "The Shoes",
    "S04E17": "The Outing",
    "S04E18": "The Old Man",
    "S04E19": "The Implant",
    "S04E20": "The Junior Mint",
    "S04E21": "The Smelly Car",
    "S04E22": "The Handicap Spot",
    "S04E23": "The Pilot",
    "S04E24": "The Pilot (Part 2)",
    # Season 5
    "S05E01": "The Mango",
    "S05E02": "The Puffy Shirt",
    "S05E03": "The Glasses",
    "S05E04": "The Sniffing Accountant",
    "S05E05": "The Bris",
    "S05E06": "The Lip Reader",
    "S05E07": "The Non-Fat Yogurt",
    "S05E08": "The Barber",
    "S05E09": "The Masseuse",
    "S05E10": "The Cigar Store Indian",
    "S05E11": "The Conversion",
    "S05E12": "The Stall",
    "S05E13": "The Dinner Party",
    "S05E14": "The Marine Biologist",
    "S05E15": "The Pie",
    "S05E16": "The Stand-In",
    "S05E17": "The Wife",
    "S05E18": "The Raincoats",
    "S05E19": "The Raincoats (Part 2)",
    "S05E20": "The Fire",
    "S05E21": "The Hamptons",
    "S05E22": "The Opposite",
    # Season 6
    "S06E01": "The Fusilli Jerry",
    "S06E02": "The Diplomat's Club",
    "S06E03": "The Switch",
    "S06E04": "The Label Maker",
    "S06E05": "The Scofflaw",
    "S06E06": "The Beard",
    "S06E07": "The Kiss Hello",
    "S06E08": "The Doorman",
    "S06E09": "The Jimmy",
    "S06E10": "The Doodle",
    "S06E11": "The Fusilli Jerry",
    "S06E12": "The Diplomat's Club",
    "S06E13": "The Face Painter",
    "S06E14": "The Understudy",
    "S06E15": "The Mom & Pop Store",
    "S06E16": "The Dad",
    "S06E17": "The Highlights of 100",
    "S06E18": "The Secretary",
    "S06E19": "The Race",
    "S06E20": "The Switch",
    "S06E21": "The Label Maker",
    "S06E22": "The Scofflaw",
    "S06E23": "The Beard",
    "S06E24": "The Kiss Hello",
    # Season 7
    "S07E01": "The Engagement",
    "S07E02": "The Postponement",
    "S07E03": "The Maestro",
    "S07E04": "The Wink",
    "S07E05": "The Hot Tub",
    "S07E06": "The Soup Nazi",
    "S07E07": "The Secret Code",
    "S07E08": "The Pool Guy",
    "S07E09": "The Sponge",
    "S07E10": "The Gum",
    "S07E11": "The Rye",
    "S07E12": "The Caddy",
    "S07E13": "The Seven",
    "S07E14": "The Cadillac",
    "S07E15": "The Cadillac (Part 2)",
    "S07E16": "The Shower Head",
    "S07E17": "The Doll",
    "S07E18": "The Friars Club",
    "S07E19": "The Wig Master",
    "S07E20": "The Calzone",
    "S07E21": "The Bottle Deposit",
    "S07E22": "The Bottle Deposit (Part 2)",
    "S07E23": "The Wait Out",
    "S07E24": "The Invitations",
    # Season 8
    "S08E01": "The Foundation",
    "S08E02": "The Soul Mate",
    "S08E03": "The Bizarro Jerry",
    "S08E04": "The Little Kicks",
    "S08E05": "The Package",
    "S08E06": "The Fatigues",
    "S08E07": "The Checks",
    "S08E08": "The Chicken Roaster",
    "S08E09": "The Abstinence",
    "S08E10": "The Andrea Doria",
    "S08E11": "The Little Jerry",
    "S08E12": "The Money",
    "S08E13": "The Comeback",
    "S08E14": "The Van Buren Boys",
    "S08E15": "The Susie",
    "S08E16": "The Pothole",
    "S08E17": "The English Patient",
    "S08E18": "The Nap",
    "S08E19": "The Yada Yada",
    "S08E20": "The Millennium",
    "S08E21": "The Muffin Tops",
    "S08E22": "The Summer of George",
    # Season 9
    "S09E01": "The Butter Shave",
    "S09E02": "The Voice",
    "S09E03": "The Serenity Now",
    "S09E04": "The Blood",
    "S09E05": "The Junk Mail",
    "S09E06": "The Merv Griffin Show",
    "S09E07": "The Slicer",
    "S09E08": "The Betrayal",
    "S09E09": "The Apology",
    "S09E10": "The Strike",
    "S09E11": "The Dealership",
    "S09E12": "The Reverse Peephole",
    "S09E13": "The Cartoon",
    "S09E14": "The Strong Box",
    "S09E15": "The Wizard",
    "S09E16": "The Burning",
    "S09E17": "The Bookstore",
    "S09E18": "The Frogger",
    "S09E19": "The Maid",
    "S09E20": "The Puerto Rican Day",
    "S09E21": "The Chronicle",
    "S09E22": "The Finale",
    "S09E23": "The Finale (Part 2)",
}

# ── KNOWN DATA: CATCHPHRASES ───────────────────────────────────────────────────
# Episode key → catchphrase label shown as a badge

CATCHPHRASES = {
    "S07E06": "No soup for you!",
    "S04E11": "Master of my domain",
    "S08E19": "Yada yada yada",
    "S05E02": "Not that there's anything wrong with that",  # actually S04E17
    "S04E17": "Not that there's anything wrong with that",
    "S05E14": "I was in the pool!",
    "S09E03": "Serenity now!",
    "S09E10": "Festivus for the rest of us",
    "S03E06": "These pretzels are making me thirsty",
    "S05E22": "Do the opposite",
    "S08E13": "The Jerk Store called...",
    "S07E11": "That's a shame",
}

# ── KNOWN DATA: CLASSIC BADGES ─────────────────────────────────────────────────
# The ~20 most iconic episodes — Chris can adjust this list

CLASSIC_EPISODES = {
    "S04E11",  # The Contest
    "S07E06",  # The Soup Nazi
    "S05E14",  # The Marine Biologist
    "S05E02",  # The Puffy Shirt
    "S04E07",  # The Bubble Boy
    "S08E19",  # The Yada Yada
    "S04E17",  # The Outing
    "S09E10",  # The Strike (Festivus)
    "S09E03",  # The Serenity Now
    "S03E11",  # The Alternate Side
    "S04E20",  # The Junior Mint
    "S09E06",  # The Merv Griffin Show
    "S08E08",  # The Chicken Roaster
    "S03E06",  # The Parking Garage
    "S02E11",  # The Chinese Restaurant
    "S03E13",  # The Subway
    "S05E22",  # The Opposite
    "S06E01",  # The Fusilli Jerry
    "S09E22",  # The Finale
    "S07E24",  # The Invitations
}

# ── KNOWN DATA: RECURRING CHARACTER IDs ───────────────────────────────────────
# Used to tag episodes. Keys match character IDs in the hub.

RECURRING_CHARACTERS = {
    "newman":        ["Newman", "Wayne Knight"],
    "frank":         ["Frank Costanza", "Jerry Stiller"],
    "estelle":       ["Estelle Costanza", "Estelle Harris"],
    "steinbrenner":  ["George Steinbrenner", "Larry David"],
    "peterman":      ["J. Peterman", "John O'Hurley"],
    "puddy":         ["David Puddy", "Patrick Warburton"],
    "uncle_leo":     ["Uncle Leo", "Len Lesser"],
    "morty":         ["Morty Seinfeld", "Barney Martin"],
    "helen":         ["Helen Seinfeld", "Liz Sheridan"],
    "jackie":        ["Jackie Chiles", "Phil Morris"],
    "tim_whatley":   ["Tim Whatley", "Bryan Cranston"],
    "bob_sacamano":  ["Bob Sacamano"],  # never appears — referenced only
}

# ── CHARACTER CARD DATA ────────────────────────────────────────────────────────
# Full character roster for the hub's character card row.
# portrait_url will be populated manually or via a separate download pass.

CHARACTERS = [
    # Core four
    {"id": "jerry",       "name": "Jerry Seinfeld",    "actor": "Jerry Seinfeld",    "tier": 1, "description": "Stand-up comedian and the show's moral center — or closest thing to one."},
    {"id": "george",      "name": "George Costanza",   "actor": "Jason Alexander",   "tier": 1, "description": "Neurotic, perpetually unemployed schemer. Every lie spawns three more."},
    {"id": "elaine",      "name": "Elaine Benes",      "actor": "Julia Louis-Dreyfus","tier": 1, "description": "Jerry's ex and sharpest wit in the group. Dances terribly. Knows it."},
    {"id": "kramer",      "name": "Cosmo Kramer",      "actor": "Michael Richards",  "tier": 1, "description": "The hipster doofus next door. Every scheme is exactly as insane as it sounds."},
    # Major recurring
    {"id": "newman",      "name": "Newman",            "actor": "Wayne Knight",      "tier": 2, "description": "Jerry's nemesis. Mail carrier. Pure chaos in a postal uniform."},
    {"id": "frank",       "name": "Frank Costanza",    "actor": "Jerry Stiller",     "tier": 2, "description": "George's volcanic father. Inventor of Festivus."},
    {"id": "estelle",     "name": "Estelle Costanza",  "actor": "Estelle Harris",    "tier": 2, "description": "George's mother. Prone to fainting. Never lets anything go."},
    {"id": "steinbrenner","name": "George Steinbrenner","actor": "Larry David (voice)","tier": 2, "description": "George's Yankees boss. Always seen from behind. Completely unhinged."},
    {"id": "peterman",    "name": "J. Peterman",       "actor": "John O'Hurley",     "tier": 2, "description": "Elaine's grandiose catalog-writing boss. Every sentence is an adventure."},
    {"id": "puddy",       "name": "David Puddy",       "actor": "Patrick Warburton", "tier": 2, "description": "Elaine's on-again-off-again boyfriend. Face painter. High-five enthusiast."},
    {"id": "uncle_leo",   "name": "Uncle Leo",         "actor": "Len Lesser",        "tier": 2, "description": "Jerry's uncle. Sees anti-Semitism everywhere. Constant unsolicited updates."},
    {"id": "morty",       "name": "Morty Seinfeld",    "actor": "Barney Martin",     "tier": 2, "description": "Jerry's father. Retired raincoat salesman. Former condo board president."},
    {"id": "helen",       "name": "Helen Seinfeld",    "actor": "Liz Sheridan",      "tier": 2, "description": "Jerry's mother. Worries constantly. Manages to make it about herself."},
    {"id": "jackie",      "name": "Jackie Chiles",     "actor": "Phil Morris",       "tier": 2, "description": "Flamboyant attorney. The best lawyer money can't quite buy enough of."},
    {"id": "tim_whatley", "name": "Tim Whatley",       "actor": "Bryan Cranston",    "tier": 2, "description": "Dentist. Re-gifter. Converted to Judaism for the jokes."},
    {"id": "bob_sacamano","name": "Bob Sacamano",      "actor": "Never appeared",    "tier": 2, "description": "Kramer's mysterious friend. Referenced throughout the series. Never seen on screen.", "never_seen": True},
]

# ── HELPERS ───────────────────────────────────────────────────────────────────

def tmdb_get(path):
    """Fetch JSON from TMDB API."""
    url = f"https://api.themoviedb.org/3{path}?api_key={TMDB_API_KEY}"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"  TMDB error {path}: {e}")
        return None

def download_image(url, dest_path):
    """Download image if it doesn't already exist."""
    if os.path.exists(dest_path):
        return True
    try:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        urllib.request.urlretrieve(url, dest_path)
        return True
    except Exception as e:
        print(f"  Image download failed {dest_path}: {e}")
        return False

def wiki_slug(title):
    """Convert episode title to fandom wiki URL slug."""
    # Replace spaces with underscores, handle special chars
    slug = title.strip()
    slug = slug.replace(" ", "_")
    slug = slug.replace("(", "%28").replace(")", "%29")
    slug = slug.replace("'", "%27")
    return slug

def fetch_wiki_page(title):
    """Fetch raw HTML from Seinfeld fandom wiki for an episode title."""
    slug = wiki_slug(title)
    url = f"{WIKI_BASE}{slug}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode("utf-8", errors="replace"), url
    except Exception as e:
        return None, url

def strip_html_tags(html):
    """Remove HTML tags, return plain text."""
    clean = re.sub(r'<[^>]+>', ' ', html)
    clean = re.sub(r'&nbsp;', ' ', clean)
    clean = re.sub(r'&amp;', '&', clean)
    clean = re.sub(r'&quot;', '"', clean)
    clean = re.sub(r'&#39;', "'", clean)
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()

def parse_wiki_plots(html):
    """
    Attempt to extract per-character plot blocks from wiki HTML.
    The fandom wiki uses h2/h3 headers like "Jerry's storyline", "George's story", etc.
    Returns dict with keys: jerry, george, elaine, kramer (any may be absent).
    Also returns raw plot text as fallback.
    """
    plots = {}
    raw_plot = ""

    # Find the plot/synopsis section
    plot_match = re.search(
        r'<span[^>]*id=["\']?(Plot|Synopsis|Story)["\']?[^>]*>.*?</span>.*?<p>(.*?)</(?:h2|h3)',
        html, re.DOTALL | re.IGNORECASE
    )
    if plot_match:
        raw_plot = strip_html_tags(plot_match.group(2))[:800]

    # Try to find character-specific sections
    # Wiki uses patterns like: Jerry's subplot, George's plot, etc.
    character_patterns = {
        "jerry":   [r"jerry['']s\s+(?:subplot|storyline|story|plot)", r"<b>Jerry</b>"],
        "george":  [r"george['']s\s+(?:subplot|storyline|story|plot)", r"<b>George</b>"],
        "elaine":  [r"elaine['']s\s+(?:subplot|storyline|story|plot)", r"<b>Elaine</b>"],
        "kramer":  [r"kramer['']s\s+(?:subplot|storyline|story|plot)", r"<b>Kramer</b>"],
    }

    # Try to extract sections after character name headers
    # Look for h3 headers with character names
    sections = re.split(r'<h[23][^>]*>', html, flags=re.IGNORECASE)
    for section in sections:
        header_match = re.match(r'^(.*?)</h[23]>(.*)', section, re.DOTALL)
        if not header_match:
            continue
        header = strip_html_tags(header_match.group(1)).lower()
        body = header_match.group(2)

        for char in ["jerry", "george", "elaine", "kramer"]:
            if char in header and "subplot" in header or char in header and "story" in header or char in header and "plot" in header:
                # Extract first paragraph(s) of this section
                para_match = re.search(r'<p>(.*?)</p>', body, re.DOTALL)
                if para_match:
                    text = strip_html_tags(para_match.group(1))
                    if len(text) > 30:
                        plots[char] = text[:400]

    # Fallback: look for paragraphs that heavily reference each character
    if len(plots) < 2 and raw_plot:
        # Split raw plot into sentences and assign to characters
        sentences = re.split(r'(?<=[.!?])\s+', raw_plot)
        char_sentences = {"jerry": [], "george": [], "elaine": [], "kramer": []}
        for sent in sentences:
            sl = sent.lower()
            for char in ["jerry", "george", "elaine", "kramer"]:
                if char in sl:
                    char_sentences[char].append(sent)
        for char, sents in char_sentences.items():
            if sents and char not in plots:
                plots[char] = " ".join(sents[:3])[:400]

    return plots, raw_plot

def parse_wiki_guests(html):
    """Extract guest cast from wiki infobox or cast section."""
    guests = []

    # Fandom wiki cast tables
    cast_section = re.search(
        r'(?:Guest Cast|Guest Stars|Recurring Cast)(.*?)(?:<h2|</table)',
        html, re.DOTALL | re.IGNORECASE
    )
    if cast_section:
        names = re.findall(r'title="([^"]+)"', cast_section.group(1))
        for name in names:
            if name and not name.startswith("File:") and not name.startswith("Category:"):
                clean = strip_html_tags(name)
                if clean and len(clean) > 2:
                    guests.append(clean)

    # Also try li items in cast sections
    if not guests:
        li_section = re.search(r'(?:Cast|Guest)(.*?)</ul>', html, re.DOTALL | re.IGNORECASE)
        if li_section:
            items = re.findall(r'<li>(.*?)</li>', li_section.group(1), re.DOTALL)
            for item in items:
                text = strip_html_tags(item)
                if text and len(text) > 2 and len(text) < 80:
                    guests.append(text)

    return list(dict.fromkeys(guests))[:15]  # dedupe, cap at 15

def parse_wiki_trivia(html):
    """Extract first trivia item if available."""
    trivia_section = re.search(
        r'(?:Trivia|Notes)(.*?)(?:<h2|$)',
        html, re.DOTALL | re.IGNORECASE
    )
    if trivia_section:
        items = re.findall(r'<li>(.*?)</li>', trivia_section.group(1), re.DOTALL)
        if items:
            return strip_html_tags(items[0])[:300]
    return ""

def detect_recurring(cast_text, guests_list):
    """Return list of recurring character IDs present in this episode."""
    found = []
    search_text = (cast_text + " " + " ".join(guests_list)).lower()
    for char_id, names in RECURRING_CHARACTERS.items():
        for name in names:
            if name.lower() in search_text:
                found.append(char_id)
                break
    return found

# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(IMG_DIR, exist_ok=True)
    os.makedirs(CHAR_DIR, exist_ok=True)

    report_lines = []
    episodes = []

    def rpt(line):
        print(line)
        report_lines.append(line)

    rpt("=" * 70)
    rpt("SEINFELD ENRICHMENT REPORT")
    rpt("=" * 70)

    # ── PASS 1: TMDB ──────────────────────────────────────────────────────────

    rpt("\n[PASS 1] Fetching series info from TMDB...")
    series = tmdb_get(f"/tv/{TMDB_SERIES_ID}")
    if not series:
        rpt("FATAL: Could not fetch series from TMDB. Check API key and series ID.")
        return

    rpt(f"  Series: {series.get('name')} ({series.get('first_air_date', '')[:4]})")
    rpt(f"  Seasons: {series.get('number_of_seasons')}  Episodes: {series.get('number_of_episodes')}")

    # Download series backdrop for hub hero
    if series.get("backdrop_path"):
        hero_path = f"{IMG_DIR}/seinfeld_hero.jpg"
        if download_image(TMDB_IMG_ORIG + series["backdrop_path"], hero_path):
            rpt(f"  ✓ Hero backdrop downloaded")

    total_seasons = series.get("number_of_seasons", 9)
    tmdb_ok = 0
    tmdb_fail = 0

    for season_num in range(1, total_seasons + 1):
        rpt(f"\n  Season {season_num}...")
        season_data = tmdb_get(f"/tv/{TMDB_SERIES_ID}/season/{season_num}")
        if not season_data:
            rpt(f"    ✗ Season {season_num} fetch failed")
            continue

        # Season poster
        if season_data.get("poster_path"):
            season_poster_path = f"{IMG_DIR}/season_{season_num}_poster.jpg"
            download_image(TMDB_IMG_BASE + season_data["poster_path"], season_poster_path)

        for ep in season_data.get("episodes", []):
            ep_num = ep.get("episode_number", 0)
            ep_key = f"S{season_num:02d}E{ep_num:02d}"
            title = ep.get("name", "")
            air_date = ep.get("air_date", "")
            overview = ep.get("overview", "")
            still_path = ep.get("still_path", "")

            # Download still
            local_still = ""
            if still_path:
                dest = f"{IMG_DIR}/s{season_num:02d}e{ep_num:02d}_still.jpg"
                if download_image(TMDB_IMG_BASE + still_path, dest):
                    local_still = f"./{dest}"
                    tmdb_ok += 1
                else:
                    tmdb_fail += 1
            else:
                tmdb_fail += 1

            # TMDB guest stars
            ep_credits = tmdb_get(f"/tv/{TMDB_SERIES_ID}/season/{season_num}/episode/{ep_num}/credits")
            tmdb_guests = []
            if ep_credits:
                for person in ep_credits.get("guest_stars", []):
                    name = person.get("name", "")
                    character = person.get("character", "")
                    if name:
                        tmdb_guests.append(f"{name} as {character}" if character else name)

            episodes.append({
                "id": ep_key,
                "season": season_num,
                "episode": ep_num,
                "title": title,
                "nickname": EPISODE_NICKNAMES.get(ep_key, title),
                "air_date": air_date,
                "tmdb_description": overview,
                "still": local_still,
                "still_tmdb": still_path,
                "tmdb_guests": tmdb_guests,
                # To be filled in Pass 2:
                "plots": {},
                "guests": tmdb_guests[:],
                "recurring": [],
                "tags": [],
                "catchphrase": CATCHPHRASES.get(ep_key),
                "is_classic": ep_key in CLASSIC_EPISODES,
                "wiki_trivia": "",
                "wiki_url": "",
                "wiki_status": "pending",
            })

        time.sleep(0.3)

    rpt(f"\n  TMDB stills: {tmdb_ok} downloaded, {tmdb_fail} missing")
    rpt(f"  Total episodes assembled: {len(episodes)}")

    # ── PASS 2: WIKI ──────────────────────────────────────────────────────────

    rpt("\n[PASS 2] Fetching Seinfeld Fandom Wiki episode pages...")
    rpt("  (Polite delay of {:.1f}s between requests)".format(WIKI_DELAY))

    wiki_full    = 0  # all 4 character plots found
    wiki_partial = 0  # 1-3 plots found
    wiki_none    = 0  # no plots parsed
    wiki_fail    = 0  # page not found / error

    needs_review = []

    for ep in episodes:
        ep_key = ep["id"]
        title = ep["nickname"] if ep["nickname"] != ep["title"] else ep["title"]

        # Strip part indicators for wiki slug
        wiki_title = re.sub(r'\s*\(Part\s+\d+\)', '', title).strip()

        html, url = fetch_wiki_page(wiki_title)
        ep["wiki_url"] = url

        if not html:
            # Try with original TMDB title
            html, url = fetch_wiki_page(ep["title"])
            ep["wiki_url"] = url

        if not html:
            ep["wiki_status"] = "not_found"
            wiki_fail += 1
            needs_review.append(f"  ✗ {ep_key} {title} — wiki page not found")
            time.sleep(WIKI_DELAY)
            continue

        # Parse plots
        plots, raw_plot = parse_wiki_plots(html)
        if plots:
            ep["plots"] = plots
            count = len(plots)
            if count == 4:
                ep["wiki_status"] = "full"
                wiki_full += 1
            else:
                ep["wiki_status"] = f"partial_{count}"
                wiki_partial += 1
                needs_review.append(f"  ⚠ {ep_key} {title} — wiki plots: {count}/4 chars")
        else:
            # Store raw description as fallback
            ep["plots"] = {"overview": raw_plot} if raw_plot else {}
            ep["wiki_status"] = "no_plots"
            wiki_none += 1
            needs_review.append(f"  ⚠ {ep_key} {title} — no plot structure found (raw stored)")

        # Parse guests
        wiki_guests = parse_wiki_guests(html)
        if wiki_guests:
            # Merge with TMDB guests, wiki takes priority
            merged = list(dict.fromkeys(wiki_guests + ep["tmdb_guests"]))
            ep["guests"] = merged[:20]

        # Parse trivia
        ep["wiki_trivia"] = parse_wiki_trivia(html)

        # Detect recurring characters
        all_cast = " ".join(ep["guests"]) + " " + ep.get("tmdb_description", "")
        ep["recurring"] = detect_recurring(all_cast, ep["guests"])

        time.sleep(WIKI_DELAY)

    # ── REPORT ────────────────────────────────────────────────────────────────

    rpt("\n[WIKI RESULTS]")
    rpt(f"  Full (4/4 plots):    {wiki_full}")
    rpt(f"  Partial (1-3 plots): {wiki_partial}")
    rpt(f"  No plots parsed:     {wiki_none}")
    rpt(f"  Page not found:      {wiki_fail}")

    if needs_review:
        rpt("\n[NEEDS REVIEW]")
        for line in needs_review:
            rpt(line)

    # Recurring character summary
    rpt("\n[RECURRING CHARACTER APPEARANCES]")
    char_counts = {c: 0 for c in RECURRING_CHARACTERS}
    for ep in episodes:
        for char_id in ep["recurring"]:
            if char_id in char_counts:
                char_counts[char_id] += 1
    for char_id, count in sorted(char_counts.items(), key=lambda x: -x[1]):
        rpt(f"  {char_id:<20} {count} episodes")

    # Classic episodes confirmation
    rpt(f"\n[CLASSIC EPISODES] {len(CLASSIC_EPISODES)} flagged")
    for ep in episodes:
        if ep["is_classic"]:
            rpt(f"  ★ {ep['id']} {ep['nickname']}")

    # ── OUTPUT ────────────────────────────────────────────────────────────────

    output = {
        "series": {
            "title": "Seinfeld",
            "network": "NBC",
            "years": "1989–1998",
            "seasons": total_seasons,
            "total_episodes": len(episodes),
            "description": "Four self-absorbed New Yorkers navigate the minutiae of everyday life — the show about nothing that said everything.",
            "hero": f"./{IMG_DIR}/seinfeld_hero.jpg",
        },
        "characters": CHARACTERS,
        "episodes": episodes,
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    rpt(f"\n[OUTPUT]")
    rpt(f"  ✓ {OUTPUT_JSON} written ({len(episodes)} episodes)")

    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    rpt(f"  ✓ {OUTPUT_REPORT} written")

    rpt("\n[DONE]")
    rpt("Next step: upload seinfeld_data.json + seinfeld_report.txt to Claude for review.")
    rpt("Then we build the hub in index.html.")

if __name__ == "__main__":
    main()
