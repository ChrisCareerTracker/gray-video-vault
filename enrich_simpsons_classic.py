#!/usr/bin/env python3
"""
Gray Video Vault — Simpsons Enrichment Script
ERA: Classic Era — Seasons 9–12 (1997–2001)
Output: simpsons_classic.json
"""

import os, sys, json, time, re, requests

BASE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(BASE, 'simpsons_classic.json')

TMDB_KEY      = '573382ec2121f69d6a89fce35293591a'
ANTHROPIC_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
TMDB_SERIES   = 456

SEASONS = list(range(9, 13))   # 9–12

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
    if not ANTHROPIC_KEY:
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
            r = requests.post('https://api.anthropic.com/v1/messages',
                              headers=headers, json=body, timeout=30)
            if r.status_code == 401:
                print('  ERROR: Anthropic API key invalid (401).')
                return {}
            if r.status_code == 429:
                print('  Anthropic rate limit — waiting 15s...')
                time.sleep(15)
                continue
            r.raise_for_status()
            text = r.json()['content'][0]['text'].strip()
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

def build_guest_list(cast):
    MAIN_CAST = {
        'Dan Castellaneta', 'Julie Kavner', 'Nancy Cartwright',
        'Yeardley Smith', 'Hank Azaria', 'Harry Shearer'
    }
    guests = []
    for member in cast:
        name      = member.get('name', '')
        character = member.get('character', '')
        if name in MAIN_CAST:
            continue
        if not name or not character:
            continue
        if any(x in character.lower() for x in ['uncredited', 'extra', 'background']):
            continue
        guests.append({'actor': name, 'character': character})
    return guests

def main():
    print('='*60)
    print('SIMPSONS ENRICHMENT — CLASSIC ERA (S9–S12)')
    print('='*60)

    if not ANTHROPIC_KEY:
        print('\nWARNING: ANTHROPIC_API_KEY not set — AI flags will be empty.\n')

    episodes = []

    for s_idx, season_num in enumerate(SEASONS):
        print(f'\n── Season {season_num} ({s_idx+1}/{len(SEASONS)}) ──')
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
                'still':    f'./images/simpsons/s{season_num:02d}e{ep_num:02d}_still.jpg' if still_path else None,
                'still_tmdb': f'https://image.tmdb.org/t/p/w500{still_path}' if still_path else None,
                'era':      'classic',
                'guests':   guest_list,
                'couch_gag':           None,
                'treehouse_of_horror': 'treehouse of horror' in title.lower(),
                'musical':             False,
                'parody':              False,
                'parody_of':           None,
                'classic':             False,
                'characters':          []
            }

            if ANTHROPIC_KEY:
                ai = anthropic_analyze({
                    'season': season_num, 'episode': ep_num,
                    'title': title, 'air_date': air_date, 'description': overview
                })
                if ai:
                    episode_record['couch_gag']  = ai.get('couch_gag')
                    episode_record['musical']     = bool(ai.get('musical', False))
                    episode_record['parody']      = bool(ai.get('parody', False))
                    episode_record['parody_of']   = ai.get('parody_of')
                    episode_record['classic']     = bool(ai.get('classic', False))
                    episode_record['characters']  = [
                        c for c in ai.get('characters', []) if c in CHARACTER_IDS
                    ]
                    if 'treehouse of horror' in title.lower():
                        episode_record['treehouse_of_horror'] = True
                time.sleep(0.5)

            episodes.append(episode_record)
            time.sleep(0.25)

    output = {
        'era':        'classic',
        'era_label':  'The Classic Era',
        'seasons':    '9–12',
        'years':      '1997–2001',
        'description': 'Still unmissable, but the cracks begin. Homer\'s Enemy. Trash of the Titans. The Principal and the Pauper.',
        'episode_count': len(episodes),
        'episodes':   episodes
    }

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f'\n{"="*60}')
    print(f'DONE — {len(episodes)} episodes written to simpsons_classic.json')
    print(f'{"="*60}')

if __name__ == '__main__':
    main()
