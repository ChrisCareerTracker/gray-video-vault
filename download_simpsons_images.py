#!/usr/bin/env python3
"""
Gray Video Vault — Simpsons Image Downloader
Downloads episode stills, character portraits, and hero/backdrop images.

Run AFTER all enrichment scripts have completed.
Run from the TV Vault folder (same location as index.html).

Usage: python3 download_simpsons_images.py
"""

import os, sys, json, time, requests

BASE = os.path.dirname(os.path.abspath(__file__))
TMDB_KEY = '573382ec2121f69d6a89fce35293591a'
TMDB_IMG = 'https://image.tmdb.org/t/p/w500'
TMDB_IMG_ORIG = 'https://image.tmdb.org/t/p/original'
TMDB_SERIES = 456

# ── Era JSON files to read ─────────────────────────────────────
ERA_FILES = [
    'simpsons_golden.json',
    'simpsons_classic.json',
    'simpsons_middle.json',
    'simpsons_modern_a.json',
    'simpsons_modern_b.json',
]

# ── Character TMDB person IDs for portrait downloads ───────────
# These are the TMDB person IDs for the voice actors / characters
# We'll fetch character images from TMDB show cast instead
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

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def download_image(url, dest_path, label=''):
    if os.path.exists(dest_path):
        return True  # Already downloaded
    try:
        r = requests.get(url, timeout=20, stream=True)
        if r.status_code == 404:
            return False
        r.raise_for_status()
        with open(dest_path, 'wb') as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f'  ✗ Failed {label}: {e}')
        if os.path.exists(dest_path):
            os.remove(dest_path)
        return False

def tmdb_get(path, params=None):
    base_params = {'api_key': TMDB_KEY}
    if params:
        base_params.update(params)
    for attempt in range(3):
        try:
            r = requests.get(f'https://api.themoviedb.org/3{path}',
                             params=base_params, timeout=15)
            if r.status_code == 429:
                print('  TMDB rate limit — waiting 10s...')
                time.sleep(10)
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt == 2:
                print(f'  TMDB error: {e}')
                return None
            time.sleep(3)
    return None

def main():
    print('='*60)
    print('SIMPSONS IMAGE DOWNLOADER')
    print('='*60)

    # ── Setup directories ──────────────────────────────────────
    img_base     = os.path.join(BASE, 'images', 'simpsons')
    char_dir     = os.path.join(img_base, 'characters')
    ensure_dir(img_base)
    ensure_dir(char_dir)
    print(f'\nSaving images to: {img_base}')

    # ── 1. Hero and backdrop ───────────────────────────────────
    print('\n── Step 1: Hero & Backdrop ──')
    series = tmdb_get(f'/tv/{TMDB_SERIES}', {'append_to_response': 'images'})
    if series:
        backdrop_path = series.get('backdrop_path', '')
        poster_path   = series.get('poster_path', '')

        if backdrop_path:
            dest = os.path.join(img_base, 'backdrop.jpg')
            url  = TMDB_IMG_ORIG + backdrop_path
            ok   = download_image(url, dest, 'backdrop')
            print(f'  {"✓" if ok else "✗"} backdrop.jpg')

            # Also save as hero (same image, hub uses both)
            dest2 = os.path.join(img_base, 'hero.jpg')
            if not os.path.exists(dest2) and os.path.exists(dest):
                import shutil
                shutil.copy(dest, dest2)
                print(f'  ✓ hero.jpg (copy of backdrop)')

        if poster_path:
            dest = os.path.join(img_base, 'poster.jpg')
            ok   = download_image(TMDB_IMG + poster_path, dest, 'poster')
            print(f'  {"✓" if ok else "✗"} poster.jpg')

    # ── 2. Episode stills ──────────────────────────────────────
    print('\n── Step 2: Episode Stills ──')
    total_eps = 0
    downloaded = 0
    skipped = 0
    missing = 0

    for era_file in ERA_FILES:
        path = os.path.join(BASE, era_file)
        if not os.path.exists(path):
            print(f'  Skipping {era_file} — not found')
            continue

        with open(path, encoding='utf-8') as f:
            data = json.load(f)

        era_label = data.get('era_label', era_file)
        episodes  = data.get('episodes', [])
        print(f'\n  {era_label} ({len(episodes)} episodes)...')

        era_dl = 0
        era_skip = 0
        era_miss = 0

        for ep in episodes:
            total_eps += 1
            season  = ep.get('season', 0)
            episode = ep.get('episode', 0)
            still_tmdb = ep.get('still_tmdb')
            fname   = f's{season:02d}e{episode:02d}_still.jpg'
            dest    = os.path.join(img_base, fname)

            if os.path.exists(dest):
                era_skip += 1
                skipped += 1
                continue

            if not still_tmdb:
                era_miss += 1
                missing += 1
                continue

            ok = download_image(still_tmdb, dest, fname)
            if ok:
                era_dl += 1
                downloaded += 1
                if era_dl % 20 == 0:
                    print(f'    ...{era_dl} downloaded so far')
            else:
                era_miss += 1
                missing += 1

            time.sleep(0.15)  # Polite to TMDB

        print(f'  ✓ {era_label}: {era_dl} new, {era_skip} already had, {era_miss} missing')

    print(f'\n  Episode stills total: {downloaded} downloaded, {skipped} already existed, {missing} unavailable')

    # ── 3. Character portraits from TMDB show cast ─────────────
    print('\n── Step 3: Character Portraits ──')
    print('  Fetching cast from TMDB...')

    # Map character IDs to the names TMDB uses
    # We'll fetch the show's aggregate credits and match by character name keywords
    char_name_map = {
        'homer':            ['Homer Simpson'],
        'marge':            ['Marge Simpson'],
        'bart':             ['Bart Simpson'],
        'lisa':             ['Lisa Simpson'],
        'maggie':           ['Maggie Simpson'],
        'burns':            ['Mr. Burns', 'C. Montgomery Burns'],
        'flanders':         ['Ned Flanders'],
        'moe':              ['Moe Szyslak', 'Moe'],
        'milhouse':         ['Milhouse Van Houten', 'Milhouse'],
        'krusty':           ['Krusty the Clown', 'Krusty'],
        'sideshow_bob':     ['Sideshow Bob', 'Robert Underdunk Terwilliger'],
        'apu':              ['Apu Nahasapeemapetilon', 'Apu'],
        'barney':           ['Barney Gumble', 'Barney'],
        'wiggum':           ['Chief Wiggum', 'Clancy Wiggum'],
        'skinner':          ['Principal Skinner', 'Seymour Skinner'],
        'smithers':         ['Waylon Smithers', 'Smithers'],
        'ralph':            ['Ralph Wiggum', 'Ralph'],
        'nelson':           ['Nelson Muntz', 'Nelson'],
        'lenny_carl':       ['Lenny Leonard', 'Carl Carlson'],
        'grandpa':          ['Grampa Simpson', 'Abraham Simpson', 'Abe Simpson'],
        'fat_tony':         ['Fat Tony', 'Marion Anthony D\'Amico'],
        'snake':            ['Snake', 'Snake Jailbird'],
        'comic_book_guy':   ['Comic Book Guy', 'Jeff Albertson'],
        'sideshow_mel':     ['Sideshow Mel'],
        'patty_selma':      ['Patty Bouvier', 'Selma Bouvier'],
        'lionel_hutz':      ['Lionel Hutz'],
        'chalmers':         ['Superintendent Chalmers', 'Gary Chalmers'],
        'kent_brockman':    ['Kent Brockman'],
        'dr_nick':          ['Dr. Nick Riviera', 'Nick Riviera'],
        'professor_frink':  ['Professor Frink', 'John Frink'],
        'cletus':           ['Cletus Spuckler', 'Cletus'],
        'dr_hibbert':       ['Dr. Hibbert', 'Julius Hibbert'],
        'mayor_quimby':     ['Mayor Quimby', 'Joseph Quimby'],
        'rainier_wolfcastle':['Rainier Wolfcastle', 'McBain'],
    }

    credits = tmdb_get(f'/tv/{TMDB_SERIES}/aggregate_credits')
    char_portraits_found = 0

    if credits:
        cast = credits.get('cast', [])
        print(f'  Found {len(cast)} cast members on TMDB')

        for char_id, name_variants in char_name_map.items():
            dest = os.path.join(char_dir, char_id + '.jpg')
            if os.path.exists(dest):
                char_portraits_found += 1
                continue

            # Find matching cast member
            matched = None
            for member in cast:
                member_roles = [r.get('character','') for r in member.get('roles',[])]
                member_roles_str = ' '.join(member_roles).lower()
                for variant in name_variants:
                    if variant.lower() in member_roles_str:
                        matched = member
                        break
                if matched:
                    break

            if matched and matched.get('profile_path'):
                url = TMDB_IMG + matched['profile_path']
                ok  = download_image(url, dest, char_id)
                if ok:
                    char_portraits_found += 1
                    print(f'  ✓ {char_id} ({matched.get("name","")})')
                else:
                    print(f'  ✗ {char_id} — download failed')
            else:
                print(f'  - {char_id} — no match found on TMDB (placeholder will show)')

            time.sleep(0.1)

    print(f'\n  Character portraits: {char_portraits_found}/{len(CHARACTER_IDS)} downloaded')

    # ── 4. Summary ─────────────────────────────────────────────
    print('\n' + '='*60)
    print('DOWNLOAD COMPLETE')
    print(f'  Episode stills:      {downloaded + skipped} total ({downloaded} new)')
    print(f'  Character portraits: {char_portraits_found}/{len(CHARACTER_IDS)}')
    print(f'  Hero/backdrop:       images/simpsons/hero.jpg + backdrop.jpg')
    print('\nNext steps:')
    print('  1. Hard refresh your browser (Cmd+Shift+R)')
    print('  2. The Simpsons hub should now show episode stills')
    print('  3. Come back to Claude to build the hub into index.html')
    print('='*60)

if __name__ == '__main__':
    main()
