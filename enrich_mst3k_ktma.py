#!/usr/bin/env python3
"""
MST3K KTMA Season Enrichment
==============================
Fetches the KTMA season (Season 0 on TMDB) of Mystery Science Theater 3000,
downloads episode stills, and appends it to the existing mst3k_data.json.

KTMA = KTMA-TV, Minneapolis, 1988-1989. Joel's pre-national run.
21 episodes, largely improvised riffing, rough production quality.
Collector's note: partial collection — not all episodes may be owned.

Run from the "TV Vault New Index and Json folders" directory.
Requires mst3k_data.json to already exist (run enrich_mst3k.py first).

Output:
  mst3k_data.json  — updated with KTMA season appended at end
  images/mst3k/    — KTMA episode stills added to existing folder
"""

import json, re, time, urllib.request
from pathlib import Path

TMDB_KEY      = '573382ec2121f69d6a89fce35293591a'
TMDB_STILL_LG = 'https://image.tmdb.org/t/p/w780'
TMDB_POSTER   = 'https://image.tmdb.org/t/p/w500'
DELAY         = 0.22
SHOW_TMDB_ID  = 1952
IMG_DIR       = Path('images/mst3k')

# Known KTMA shorts from MST3K records
# KTMA used Radar Men from the Moon and The Phantom Creeps as serials
KTMA_SHORTS = {
    2:  ['Radar Men from the Moon Chapter 1: Commando Cody'],
    3:  ['Radar Men from the Moon Chapter 2: Molten Terror'],
    4:  ['Radar Men from the Moon Chapter 3: Bridge of Death'],
    5:  ['Radar Men from the Moon Chapter 4: Flight to Destruction'],
    6:  ['Radar Men from the Moon Chapter 5: The Unearthly Roots'],
    7:  ['Radar Men from the Moon Chapter 6: Hills of Death'],
    8:  ['Radar Men from the Moon Chapter 7: Camouflaged Destruction'],
    9:  ['Radar Men from the Moon Chapter 8: The Invisible Enemy'],
    10: ['Radar Men from the Moon Chapter 9: Battle in the Stratosphere'],
    11: ['Radar Men from the Moon Chapter 10: Mass Destruction'],
    12: ['The Phantom Creeps Chapter 1: The Menacing Power'],
    13: ['The Phantom Creeps Chapter 2: Death Stalks the Highway'],
    14: ['The Phantom Creeps Chapter 3: Crashing Timbers'],
    15: ['The Phantom Creeps Chapter 4: Invisible Terror'],
    16: ['The Phantom Creeps Chapter 5: Menace from the Past'],
    17: ['The Phantom Creeps Chapter 6: The Evil Master'],
    18: ['The Phantom Creeps Chapter 7: The Fatal Experiment'],
    19: ['The Phantom Creeps Chapter 8: Trapped'],
    20: ['The Phantom Creeps Chapter 9: Battle of the Giants'],
    21: ['The Phantom Creeps Chapter 10: The Final Reckoning'],
}

def download(url, dest_path, label=''):
    if dest_path.exists() and dest_path.stat().st_size > 500:
        return True
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read()
        if len(data) < 500:
            return False
        dest_path.write_bytes(data)
        return True
    except Exception as e:
        print(f"  FAIL {label}: {e}")
        return False

def tmdb_api(path):
    url = f"https://api.themoviedb.org/3{path}?api_key={TMDB_KEY}&language=en-US"
    try:
        with urllib.request.urlopen(url, timeout=12) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  API error {path}: {e}")
        return None

def main():
    print("MST3K KTMA Season Enrichment")
    print("=" * 50)

    # Load existing data
    if not Path('mst3k_data.json').exists():
        print("ERROR: mst3k_data.json not found. Run enrich_mst3k.py first.")
        return

    with open('mst3k_data.json') as f:
        data = json.load(f)

    existing_seasons = [s['num'] for s in data['seasons']]
    print(f"Existing seasons: {existing_seasons}")
    print(f"Existing episodes: {sum(len(s['episodes']) for s in data['seasons'])}")

    if 0 in existing_seasons:
        print("KTMA season already present. Remove it first if you want to re-fetch.")
        return

    IMG_DIR.mkdir(parents=True, exist_ok=True)

    # Fetch KTMA = Season 0 on TMDB
    print("\nFetching KTMA season (Season 0 on TMDB)...")
    season_data = tmdb_api(f'/tv/{SHOW_TMDB_ID}/season/0')
    time.sleep(DELAY)

    if not season_data or not season_data.get('episodes'):
        print("ERROR: No KTMA data returned from TMDB.")
        return

    tmdb_eps = {ep['episode_number']: ep for ep in season_data['episodes']}
    print(f"TMDB returned {len(tmdb_eps)} KTMA episodes")

    # Download season poster
    season_poster = ''
    if season_data.get('poster_path'):
        url = TMDB_POSTER + season_data['poster_path']
        dest = IMG_DIR / 'season_ktma_poster.jpg'
        if download(url, dest, 'KTMA poster'):
            season_poster = './images/mst3k/season_ktma_poster.jpg'
            print("  ✓ KTMA poster downloaded")
        time.sleep(DELAY)

    episodes = []
    for ep_num in sorted(tmdb_eps.keys()):
        tmdb_ep = tmdb_eps[ep_num]

        movie    = tmdb_ep.get('name', f'Episode {ep_num}').strip()
        overview = tmdb_ep.get('overview', '')
        airdate  = tmdb_ep.get('air_date', '')
        still_path = tmdb_ep.get('still_path', '')
        shorts   = KTMA_SHORTS.get(ep_num, [])

        # Download still
        still_local = ''
        if still_path:
            filename = f'sktmae{ep_num:02d}_still.jpg'
            dest = IMG_DIR / filename
            url = TMDB_STILL_LG + still_path
            if download(url, dest, f'KTMAE{ep_num}'):
                still_local = f'./images/mst3k/{filename}'
            time.sleep(DELAY)

        has_still = '✓' if still_local else '✗'
        print(f"  K{ep_num:02d} [Joel] {movie[:40]:<40} still={has_still} shorts={len(shorts)}")

        episodes.append({
            'num':       ep_num,
            'title':     movie,
            'host':      'Joel',
            'airdate':   airdate,
            'shorts':    shorts,
            'has_short': len(shorts) > 0,
            'desc':      overview,
            'still':     still_local,
        })

    ktma_season = {
        'num':      0,
        'year':     '1988-1989',
        'network':  'KTMA-TV',
        'tagline':  'The pre-national run — raw, improvised riffing from Minneapolis before the world was watching.',
        'poster':   season_poster,
        'label':    'KTMA',
        'collectionNote': 'Partial collection',
        'episodes': episodes,
    }

    # Append KTMA at the end (bonus content)
    data['seasons'].append(ktma_season)

    total = sum(len(s['episodes']) for s in data['seasons'])
    stills = sum(1 for s in data['seasons'] for e in s['episodes'] if e.get('still'))
    print(f"\n✓ KTMA season added: {len(episodes)} episodes")
    print(f"  New total: {total} episodes ({stills} with stills)")

    with open('mst3k_data.json', 'w') as f:
        json.dump(data, f, separators=(',', ':'), ensure_ascii=False)
    print("✓ mst3k_data.json updated")
    print("\nNext: upload updated mst3k_data.json to Claude to update the hub.")

if __name__ == '__main__':
    main()
