#!/usr/bin/env python3
"""
fix_season6.py
Re-pulls Season 6 Seinfeld episode data from TMDB and regenerates
AI plot summaries. Replaces only Season 6 in seinfeld_data.json.
Run from the TV Vault folder.
"""
import json, os, time, urllib.request, urllib.parse

# ── Config ────────────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE, 'seinfeld_data.json')
TMDB_KEY = '573382ec2121f69d6a89fce35293591a'
TMDB_SERIES_ID = 1400  # Seinfeld
SEASON = 6
STILL_DIR = os.path.join(BASE, 'images', 'seinfeld')

# ── Load existing data ────────────────────────────────────────────────────────
print('Loading seinfeld_data.json...')
with open(DATA_FILE, encoding='utf-8') as f:
    data = json.load(f)

other_eps = [ep for ep in data['episodes'] if ep['season'] != SEASON]
print(f'Keeping {len(other_eps)} episodes from other seasons')

# ── Fetch Season 6 from TMDB ──────────────────────────────────────────────────
print(f'\nFetching Season {SEASON} from TMDB...')
url = f'https://api.themoviedb.org/3/tv/{TMDB_SERIES_ID}/season/{SEASON}?api_key={TMDB_KEY}&append_to_response=credits'
with urllib.request.urlopen(url) as r:
    season_data = json.loads(r.read())

tmdb_eps = season_data.get('episodes', [])
print(f'TMDB returned {len(tmdb_eps)} episodes for Season {SEASON}')

# ── Download stills ───────────────────────────────────────────────────────────
os.makedirs(STILL_DIR, exist_ok=True)

def download_still(path, ep_num):
    if not path:
        return None
    filename = f's{SEASON:02d}e{ep_num:02d}_still.jpg'
    dest = os.path.join(STILL_DIR, filename)
    if os.path.exists(dest):
        print(f'  Still exists: {filename}')
        return f'./images/seinfeld/{filename}'
    url = f'https://image.tmdb.org/t/p/w780{path}'
    try:
        urllib.request.urlretrieve(url, dest)
        print(f'  Downloaded: {filename}')
        return f'./images/seinfeld/{filename}'
    except Exception as e:
        print(f'  Failed {filename}: {e}')
        return None

# ── Known recurring characters for Season 6 ──────────────────────────────────
RECURRING_MAP = {
    'Wayne Knight': 'newman',
    'Jerry Stiller': 'frank',
    'Estelle Harris': 'estelle',
    'Larry Thomas': 'soup_nazi',
    'John O\'Hurley': 'peterman',
    'Patrick Warburton': 'puddy',
    'Len Lesser': 'uncle_leo',
    'Barney Martin': 'morty',
    'Liz Sheridan': 'helen',
    'Phil Morris': 'jackie',
    'Bryan Cranston': 'tim_whatley',
    'Heidi Swedberg': 'susan',
    'Brian George': 'babu',
    'Peter Crombie': 'joe_davola',
    'Mark Metcalf': 'maestro',
    'Peter Keleghan': 'lloyd_braun',
    'Larry David': 'steinbrenner',
    'Philip Baker Hall': 'joe_bookman',
}

CLASSIC_EPISODES = {
    'The Soup', 'The Label Maker', 'The Beard', 'The Jimmy',
    'The Fusilli Jerry', "The Diplomat's Club", 'The Face Painter',
    'The Understudy', 'The Switch'
}

# ── Build new Season 6 episodes ───────────────────────────────────────────────
print(f'\nBuilding Season {SEASON} episode data...')
new_s6_eps = []

for ep in tmdb_eps:
    ep_num = ep['episode_number']
    title = ep.get('name', f'Episode {ep_num}')
    air_date = ep.get('air_date', '')
    overview = ep.get('overview', '')
    still_path = ep.get('still_path', '')

    print(f'\nS{SEASON}E{ep_num:02d}: {title}')

    # Download still
    still_local = download_still(still_path, ep_num)

    # Get guest stars
    guests = []
    guest_data = ep.get('guest_stars', [])
    for g in guest_data[:15]:
        name = g.get('name', '')
        char = g.get('character', '')
        if name:
            guests.append(f'{name} as {char}' if char else name)

    # Detect recurring characters
    recurring = []
    all_cast = [g.get('name', '') for g in guest_data]
    for actor, char_id in RECURRING_MAP.items():
        if actor in all_cast and char_id not in recurring:
            recurring.append(char_id)

    ep_obj = {
        'id': f'S{SEASON:02d}E{ep_num:02d}',
        'season': SEASON,
        'episode': ep_num,
        'title': title,
        'nickname': title,
        'air_date': air_date,
        'tmdb_description': overview,
        'still': still_local,
        'guests': guests,
        'recurring': recurring,
        'is_classic': title in CLASSIC_EPISODES,
        'plots': {}
    }
    new_s6_eps.append(ep_obj)
    time.sleep(0.25)

print(f'\nBuilt {len(new_s6_eps)} Season {SEASON} episodes')

# ── Generate AI plot summaries ────────────────────────────────────────────────
try:
    import anthropic
    client = anthropic.Anthropic()
    CHARS = ['jerry', 'george', 'elaine', 'kramer']

    print(f'\nGenerating plot summaries for {len(new_s6_eps)} episodes...')
    for i, ep in enumerate(new_s6_eps):
        desc = ep.get('tmdb_description', '')
        if not desc:
            print(f'  S{SEASON}E{ep["episode"]:02d}: {ep["title"]} — no description, skipping')
            continue

        print(f'  [{i+1}/{len(new_s6_eps)}] {ep["title"]}...')
        prompt = f"""Seinfeld episode "{ep['title']}" (Season {SEASON}, Episode {ep['episode']}).
Air date: {ep.get('air_date', 'unknown')}.
Overview: {desc}

Write a single sentence (max 25 words) describing what each main character does in this episode.
Only include characters who have a meaningful role. If a character barely appears, omit them.
Respond in this exact JSON format with no other text:
{{"jerry": "...", "george": "...", "elaine": "...", "kramer": "..."}}
Use null for any character with no meaningful role."""

        try:
            msg = client.messages.create(
                model='claude-opus-4-5',
                max_tokens=300,
                messages=[{'role': 'user', 'content': prompt}]
            )
            raw = msg.content[0].text.strip()
            plots_raw = json.loads(raw)
            plots = {k: v for k, v in plots_raw.items() if v and v != 'null'}
            ep['plots'] = plots
            print(f'    Got plots for: {list(plots.keys())}')
        except Exception as e:
            print(f'    Plot error: {e}')
            ep['plots'] = {}
        time.sleep(1)

except ImportError:
    print('\nAnthopic not installed — skipping plot summaries')
    print('Run: pip3 install anthropic --break-system-packages')

# ── Merge and save ────────────────────────────────────────────────────────────
all_eps = other_eps + new_s6_eps
all_eps.sort(key=lambda e: (e['season'], e['episode']))
data['episodes'] = all_eps

with open(DATA_FILE, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f'\n✓ Done! seinfeld_data.json updated with {len(new_s6_eps)} fresh Season {SEASON} episodes')
print(f'  Total episodes: {len(all_eps)}')

# Quick sanity check
s6 = [ep for ep in all_eps if ep['season'] == SEASON]
print(f'\nSeason {SEASON} sanity check:')
for ep in s6:
    plots = list(ep.get('plots', {}).keys())
    print(f'  S{SEASON}E{ep["episode"]:02d}: {ep["title"]} | plots: {plots}')
