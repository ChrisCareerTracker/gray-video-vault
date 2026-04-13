#!/usr/bin/env python3
"""
Gray Video Vault — Simpsons Character Portrait Downloader
Downloads character artwork from TMDB for the character strip.

Run from the TV Vault folder (same location as index.html).
Usage: python3 download_simpsons_characters.py
"""

import os, json, time, requests

BASE      = os.path.dirname(os.path.abspath(__file__))
CHAR_DIR  = os.path.join(BASE, 'images', 'simpsons', 'characters')
TMDB_KEY  = '573382ec2121f69d6a89fce35293591a'
TMDB_SERIES = 456

os.makedirs(CHAR_DIR, exist_ok=True)

def tmdb_get(path, params=None):
    p = {'api_key': TMDB_KEY}
    if params: p.update(params)
    for attempt in range(3):
        try:
            r = requests.get(f'https://api.themoviedb.org/3{path}', params=p, timeout=15)
            if r.status_code == 429:
                print('  Rate limit — waiting 10s...')
                time.sleep(10); continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt == 2: print(f'  Error: {e}'); return None
            time.sleep(3)
    return None

def download(url, dest, label=''):
    if os.path.exists(dest):
        print(f'  ✓ {label} (already exists)')
        return True
    try:
        r = requests.get(url, timeout=20, stream=True)
        if r.status_code == 404: return False
        r.raise_for_status()
        with open(dest, 'wb') as f:
            for chunk in r.iter_content(8192): f.write(chunk)
        print(f'  ✓ {label}')
        return True
    except Exception as e:
        print(f'  ✗ {label}: {e}')
        if os.path.exists(dest): os.remove(dest)
        return False

# ── Character name → search terms for TMDB person search ──────
# We search TMDB for each character by name and grab their profile image
# These are the ANIMATED character names as TMDB knows them
CHARACTERS = [
    # (file_id,        search_name,               fallback_search)
    ('homer',          'Homer Simpson',             'Homer Simpson Simpsons'),
    ('marge',          'Marge Simpson',             'Marge Simpson Simpsons'),
    ('bart',           'Bart Simpson',              'Bart Simpson Simpsons'),
    ('lisa',           'Lisa Simpson',              'Lisa Simpson Simpsons'),
    ('maggie',         'Maggie Simpson',            'Maggie Simpson Simpsons'),
    ('burns',          'Mr. Burns',                 'Montgomery Burns Simpsons'),
    ('flanders',       'Ned Flanders',              'Ned Flanders Simpsons'),
    ('moe',            'Moe Szyslak',               'Moe Simpsons bartender'),
    ('milhouse',       'Milhouse Van Houten',       'Milhouse Simpsons'),
    ('krusty',         'Krusty the Clown',          'Krusty Simpsons'),
    ('sideshow_bob',   'Sideshow Bob',              'Robert Terwilliger Simpsons'),
    ('apu',            'Apu Nahasapeemapetilon',    'Apu Simpsons'),
    ('barney',         'Barney Gumble',             'Barney Gumble Simpsons'),
    ('wiggum',         'Chief Wiggum',              'Clancy Wiggum Simpsons'),
    ('skinner',        'Principal Skinner',         'Seymour Skinner Simpsons'),
    ('smithers',       'Waylon Smithers',           'Smithers Simpsons'),
    ('ralph',          'Ralph Wiggum',              'Ralph Wiggum Simpsons'),
    ('nelson',         'Nelson Muntz',              'Nelson Muntz Simpsons'),
    ('lenny_carl',     'Lenny Leonard',             'Lenny Carl Simpsons'),
    ('grandpa',        'Abraham Simpson',           'Grampa Simpson Simpsons'),
    ('fat_tony',       'Fat Tony',                  'Fat Tony Simpsons'),
    ('snake',          'Snake Jailbird',            'Snake Simpsons'),
    ('comic_book_guy', 'Comic Book Guy',            'Comic Book Guy Simpsons Jeff Albertson'),
    ('sideshow_mel',   'Sideshow Mel',              'Sideshow Mel Simpsons'),
    ('patty_selma',    'Patty Bouvier',             'Patty Selma Simpsons'),
    ('lionel_hutz',    'Lionel Hutz',               'Lionel Hutz Simpsons'),
    ('chalmers',       'Superintendent Chalmers',   'Chalmers Simpsons'),
    ('kent_brockman',  'Kent Brockman',             'Kent Brockman Simpsons'),
    ('dr_nick',        'Dr. Nick Riviera',          'Dr Nick Simpsons'),
    ('professor_frink','Professor Frink',           'Frink Simpsons'),
    ('cletus',         'Cletus Spuckler',           'Cletus Simpsons'),
    ('dr_hibbert',     'Dr. Hibbert',               'Julius Hibbert Simpsons'),
    ('mayor_quimby',   'Mayor Quimby',              'Mayor Quimby Simpsons'),
    ('rainier_wolfcastle', 'Rainier Wolfcastle',    'McBain Simpsons'),
]

# ── Strategy 1: TMDB show's aggregate_credits character images ─
# TMDB stores character profile paths on cast entries
print('='*60)
print('SIMPSONS CHARACTER PORTRAIT DOWNLOADER')
print('='*60)
print('\nStrategy 1: Fetching show aggregate credits...')

credits = tmdb_get(f'/tv/{TMDB_SERIES}/aggregate_credits')
char_image_map = {}  # character_name_lower -> profile_path

if credits:
    for member in credits.get('cast', []):
        profile = member.get('profile_path', '')
        if not profile: continue
        for role in member.get('roles', []):
            char_name = role.get('character', '').lower()
            if char_name and char_name not in char_image_map:
                char_image_map[char_name] = profile

    print(f'  Found {len(char_image_map)} character image entries')

# Match our characters against the credits
found_s1 = 0
for char_id, search_name, _ in CHARACTERS:
    dest = os.path.join(CHAR_DIR, char_id + '.jpg')
    if os.path.exists(dest):
        found_s1 += 1
        continue

    search_lower = search_name.lower()
    profile_path = None

    # Exact match first
    if search_lower in char_image_map:
        profile_path = char_image_map[search_lower]
    else:
        # Partial match
        for cname, cpath in char_image_map.items():
            first_word = search_lower.split()[0]
            if len(first_word) > 3 and first_word in cname:
                profile_path = cpath
                break

    if profile_path:
        url = f'https://image.tmdb.org/t/p/w185{profile_path}'
        ok = download(url, dest, f'{char_id} ({search_name})')
        if ok: found_s1 += 1

print(f'\nStrategy 1 result: {found_s1}/{len(CHARACTERS)} portraits found')

# ── Strategy 2: TMDB person search for remaining ──────────────
print('\nStrategy 2: TMDB person search for remaining...')
found_s2 = 0

for char_id, search_name, fallback in CHARACTERS:
    dest = os.path.join(CHAR_DIR, char_id + '.jpg')
    if os.path.exists(dest):
        found_s2 += 1
        continue

    # Try primary search, then fallback
    for query in [search_name, fallback]:
        results = tmdb_get('/search/person', {'query': query, 'include_adult': 'false'})
        if not results: continue

        for result in results.get('results', [])[:3]:
            profile = result.get('profile_path', '')
            if not profile: continue
            # Make sure it's plausibly related to Simpsons
            known_for = [k.get('name','') + ' ' + k.get('title','') for k in result.get('known_for', [])]
            known_str = ' '.join(known_for).lower()
            if 'simpsons' not in known_str and 'springfield' not in known_str:
                continue
            url = f'https://image.tmdb.org/t/p/w185{profile}'
            ok = download(url, dest, f'{char_id} via person search')
            if ok: found_s2 += 1; break
        if os.path.exists(dest): break
        time.sleep(0.2)

print(f'Strategy 2 result: {found_s2}/{len(CHARACTERS)} portraits found')

# ── Strategy 3: TMDB show images — grab season posters ────────
# As a last resort for any remaining, download character stills
# from season posters which often feature main characters
print('\nStrategy 3: Checking remaining gaps...')
still_missing = []
for char_id, search_name, _ in CHARACTERS:
    dest = os.path.join(CHAR_DIR, char_id + '.jpg')
    if not os.path.exists(dest):
        still_missing.append((char_id, search_name))

if still_missing:
    print(f'\n  {len(still_missing)} characters still need manual portraits:')
    for char_id, name in still_missing:
        print(f'    - {char_id} ({name})')
        print(f'      → Save as: images/simpsons/characters/{char_id}.jpg')
else:
    print('  All characters have portraits!')

# ── Summary ────────────────────────────────────────────────────
total = sum(1 for cid,_,_ in CHARACTERS if os.path.exists(os.path.join(CHAR_DIR, cid+'.jpg')))
print(f'\n{"="*60}')
print(f'DONE — {total}/{len(CHARACTERS)} character portraits downloaded')
print(f'Saved to: {CHAR_DIR}')
if total < len(CHARACTERS):
    print(f'\n{len(CHARACTERS)-total} missing — add manually or they show initials placeholder')
print('='*60)
