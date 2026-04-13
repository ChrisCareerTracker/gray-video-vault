#!/usr/bin/env python3
"""
Gray Video Vault — Simpsons Enrichment Script
ERA: Golden Age — Seasons 1–8 (1989–1997)
Output: simpsons_golden.json
"""

import os, sys, json, time, re, requests

# ── Paths ──────────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(BASE, 'simpsons_golden.json')

# ── API Keys ───────────────────────────────────────────────────────────────
TMDB_KEY      = '573382ec2121f69d6a89fce35293591a'
ANTHROPIC_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
TMDB_SERIES   = 456   # The Simpsons on TMDB

SEASONS = list(range(1, 9))   # 1–8

# ── Character ID list (for AI to tag) ─────────────────────────────────────
CHARACTER_IDS = [
    'homer','marge','bart','lisa','maggie',
    'burns','flanders','moe','milhouse','krusty',
    'sideshow_bob','apu','barney','wiggum','skinner',
    'smithers','ralph','nelson','lenny_carl','grandpa',
    'fat_tony','snake','comic_book_guy','sideshow_mel',
    'patty_selma','lionel_hutz','chalmers','kent_brockman',
    'dr_nick','professor_frink','cletus','dr_hibbert',
    'mayor_quimby','rainier_wolfcastle'
]

# ── Helpers ────────────────────────────────────────────────────────────────
def tmdb_get(path, params=None):
    base_params = {'api_key': TMDB_KEY}
    if params:
        base_params.update(params)
    url = f'https://api.themoviedb.org/3{path}'
    for attempt in range(3):
        try:
            r = requests.get(url, params=base_params, timeout=15)
            if r.status_code == 429:
                print('  TMDB rate limit — waiting 10s...')
                time.sleep(10)
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt == 2:
                print(f'  TMDB error on {path}: {e}')
                return None
            time.sleep(3)
    return None

def anthropic_analyze(episode_data):
    """Call Anthropic API to flag musical, parody, classic, characters, couch_gag."""
    if not ANTHROPIC_KEY:
        print('  WARNING: No ANTHROPIC_API_KEY set — skipping AI flags.')
        return {}

    prompt = f"""You are an expert on The Simpsons TV show. Analyze this episode and return ONLY a JSON object with no explanation.

Episode: S{episode_data['season']:02d}E{episode_data['episode']:02d} — "{episode_data['title']}"
Air date: {episode_data.get('air_date', 'unknown')}
Description: {episode_data.get('description', 'No description available')}

Return ONLY this JSON structure (no markdown, no extra text):
{{
  "couch_gag": "Brief 1-sentence description of the couch gag for this episode. If unknown, write null.",
  "musical": true or false — true if the episode features original songs performed by characters (even one notable song counts),
  "parody": true or false — true if the episode is structured as a parody or tribute to a specific film, TV show, genre, or cultural phenomenon,
  "parody_of": "What it parodies, e.g. 'Cape Fear', 'Hee Haw', null if parody is false",
  "classic": true or false — true if this is a widely considered fan-essential or critically acclaimed episode,
  "characters": array of character IDs from this list that have significant screen time or plot relevance in this episode:
    {json.dumps(CHARACTER_IDS)}
}}

Be accurate. For couch_gag, recall the specific gag if you know it. For characters, only include IDs where the character meaningfully appears."""

    headers = {
        'x-api-key': ANTHROPIC_KEY,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json'
    }
    body = {
        'model': 'claude-sonnet-4-20250514',
        'max_tokens': 1000,
        'messages': [{'role': 'user', 'content': prompt}]
    }

    for attempt in range(3):
        try:
            r = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers=headers,
                json=body,
                timeout=30
            )
            if r.status_code == 401:
                print('  ERROR: Anthropic API key invalid (401). Check your key.')
                return {}
            if r.status_code == 429:
                print('  Anthropic rate limit — waiting 15s...')
                time.sleep(15)
                continue
            r.raise_for_status()
            data = r.json()
            text = data['content'][0]['text'].strip()
            # Strip any accidental markdown fences
            text = re.sub(r'^```[a-z]*\n?', '', text)
            text = re.sub(r'\n?```$', '', text)
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f'  AI JSON parse error on {episode_data["title"]}: {e}')
            return {}
        except Exception as e:
            if attempt == 2:
                print(f'  Anthropic error on {episode_data["title"]}: {e}')
                return {}
            time.sleep(5)
    return {}

def build_still_path(season, episode, filename):
    if not filename:
        return None
    return f'./images/simpsons/s{season:02d}e{episode:02d}_still.jpg'

def build_guest_list(cast):
    """Extract guest cast — exclude main 6 voice actors."""
    MAIN_CAST = {
        'Dan Castellaneta', 'Julie Kavner', 'Nancy Cartwright',
        'Yeardley Smith', 'Hank Azaria', 'Harry Shearer'
    }
    guests = []
    for member in cast:
        name = member.get('name', '')
        character = member.get('character', '')
        if name in MAIN_CAST:
            continue
        if not name or not character:
            continue
        # Skip generic extras
        if any(x in character.lower() for x in ['uncredited', 'extra', 'background']):
            continue
        guests.append({'actor': name, 'character': character})
    return guests

# ── Main ───────────────────────────────────────────────────────────────────
def main():
    print('='*60)
    print('SIMPSONS ENRICHMENT — GOLDEN AGE (S1–S8)')
    print('='*60)

    if not ANTHROPIC_KEY:
        print('\nWARNING: ANTHROPIC_API_KEY not set!')
        print('Set it with: export ANTHROPIC_API_KEY=sk-ant-...')
        print('AI flags (musical, parody, classic, characters, couch_gag) will be empty.\n')

    episodes = []
    total_seasons = len(SEASONS)

    for s_idx, season_num in enumerate(SEASONS):
        print(f'\n── Season {season_num} ({s_idx+1}/{total_seasons}) ──')
        season_data = tmdb_get(f'/tv/{TMDB_SERIES}/season/{season_num}')
        if not season_data:
            print(f'  Could not fetch season {season_num} — skipping.')
            continue

        season_eps = season_data.get('episodes', [])
        print(f'  Found {len(season_eps)} episodes')

        for ep in season_eps:
            ep_num   = ep.get('episode_number', 0)
            title    = ep.get('name', '')
            air_date = ep.get('air_date', '')
            overview = ep.get('overview', '')
            still_path = ep.get('still_path', '')

            print(f'  S{season_num:02d}E{ep_num:02d} — {title}')

            # Fetch full episode details for cast
            ep_detail = tmdb_get(
                f'/tv/{TMDB_SERIES}/season/{season_num}/episode/{ep_num}',
                {'append_to_response': 'credits'}
            )

            guest_list = []
            if ep_detail and 'credits' in ep_detail:
                all_cast = ep_detail['credits'].get('cast', []) + ep_detail['credits'].get('guest_stars', [])
                guest_list = build_guest_list(all_cast)
            elif ep_detail and 'guest_stars' in ep_detail:
                guest_list = build_guest_list(ep_detail.get('guest_stars', []))

            episode_record = {
                'season':   season_num,
                'episode':  ep_num,
                'title':    title,
                'air_date': air_date,
                'description': overview,
                'still':    build_still_path(season_num, ep_num, still_path),
                'still_tmdb': f'https://image.tmdb.org/t/p/w500{still_path}' if still_path else None,
                'era':      'golden',
                'guests':   guest_list,
                # AI-filled fields (populated below)
                'couch_gag':            None,
                'treehouse_of_horror':  'treehouse of horror' in title.lower(),
                'musical':              False,
                'parody':               False,
                'parody_of':            None,
                'classic':              False,
                'characters':           []
            }

            # AI enrichment
            if ANTHROPIC_KEY:
                ai = anthropic_analyze({
                    'season':      season_num,
                    'episode':     ep_num,
                    'title':       title,
                    'air_date':    air_date,
                    'description': overview
                })
                if ai:
                    episode_record['couch_gag']   = ai.get('couch_gag')
                    episode_record['musical']      = bool(ai.get('musical', False))
                    episode_record['parody']       = bool(ai.get('parody', False))
                    episode_record['parody_of']    = ai.get('parody_of')
                    episode_record['classic']      = bool(ai.get('classic', False))
                    episode_record['characters']   = [
                        c for c in ai.get('characters', []) if c in CHARACTER_IDS
                    ]
                    # Never override TMDB-detected ToH
                    if 'treehouse of horror' in title.lower():
                        episode_record['treehouse_of_horror'] = True

                time.sleep(0.5)   # Be polite to Anthropic API

            episodes.append(episode_record)
            time.sleep(0.25)   # Be polite to TMDB

    # ── Write output ──────────────────────────────────────────────────────
    output = {
        'era':        'golden',
        'era_label':  'The Golden Age',
        'seasons':    '1–8',
        'years':      '1989–1997',
        'description': 'The untouchable era. From Homer\'s Odyssey to You Only Move Twice. When nothing could go wrong.',
        'episode_count': len(episodes),
        'episodes':   episodes
    }

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f'\n{"="*60}')
    print(f'DONE — {len(episodes)} episodes written to simpsons_golden.json')
    print(f'{"="*60}')

if __name__ == '__main__':
    main()
