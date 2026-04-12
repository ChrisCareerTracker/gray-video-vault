#!/usr/bin/env python3
"""
fetch_missing_posters.py
Run this locally to fill in missing poster/backdrop paths for 24 cartoons.
Usage: python3 fetch_missing_posters.py looney_tunes_enriched_final_v7.json
It will produce looney_tunes_enriched_final_v7_patched.json
"""

import json
import sys
import time
import urllib.request
import urllib.error

TMDB_KEY = '573382ec2121f69d6a89fce35293591a'

def tmdb_fetch(tmdb_id):
    url = f'https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={TMDB_KEY}'
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f'  HTTP {e.code} for id={tmdb_id}')
        return None
    except Exception as e:
        print(f'  Error for id={tmdb_id}: {e}')
        return None

def main():
    infile = sys.argv[1] if len(sys.argv) > 1 else 'looney_tunes_enriched_final_v7.json'
    outfile = infile.replace('.json', '_patched.json')

    with open(infile) as f:
        data = json.load(f)

    patched = 0
    for decade_key, dd in data['by_decade'].items():
        for c in dd['cartoons']:
            if not c.get('poster') and c.get('tmdb_id'):
                print(f'Fetching: {c["year"]} "{c["title"]}" (id={c["tmdb_id"]})...', end=' ')
                d = tmdb_fetch(c['tmdb_id'])
                if d:
                    poster = d.get('poster_path') or ''
                    backdrop = d.get('backdrop_path') or ''
                    c['poster'] = poster
                    c['backdrop'] = backdrop
                    if poster:
                        print(f'✓ poster={poster[:30]}')
                        patched += 1
                    else:
                        print('(no poster on TMDB)')
                else:
                    print('FAILED')
                time.sleep(0.25)  # rate limit

    with open(outfile, 'w') as f:
        json.dump(data, f, separators=(',', ':'))

    total = sum(len(dd['cartoons']) for dd in data['by_decade'].values())
    still_missing = sum(1 for dd in data['by_decade'].values()
                        for c in dd['cartoons'] if not c.get('poster'))
    print(f'\nDone. Patched {patched} posters.')
    print(f'Still missing: {still_missing}/{total}')
    print(f'Output: {outfile}')

if __name__ == '__main__':
    main()
