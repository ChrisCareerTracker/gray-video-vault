#!/usr/bin/env python3
"""
Gray Video Vault — Simpsons Guest Actor Headshot Downloader
Downloads TMDB profile photos for the top guest stars.
Saves to images/simpsons/guests/ for the Guest Hall of Fame montage.

No API key needed — uses TMDB public API only.
Run from the TV Vault folder.
Usage: python3 download_simpsons_guests.py
"""

import os, json, time, re, requests

BASE      = os.path.dirname(os.path.abspath(__file__))
GUEST_DIR = os.path.join(BASE, 'images', 'simpsons', 'guests')
TMDB_KEY  = '573382ec2121f69d6a89fce35293591a'
TMDB_IMG  = 'https://image.tmdb.org/t/p/w185'

ERA_FILES = [
    'simpsons_golden.json',
    'simpsons_classic.json',
    'simpsons_middle.json',
    'simpsons_modern_a.json',
    'simpsons_modern_b.json',
]

MAIN_CAST = {
    'Dan Castellaneta', 'Julie Kavner', 'Nancy Cartwright',
    'Yeardley Smith', 'Hank Azaria', 'Harry Shearer'
}

os.makedirs(GUEST_DIR, exist_ok=True)

def tmdb_search_person(name):
    try:
        r = requests.get(
            'https://api.themoviedb.org/3/search/person',
            params={'api_key': TMDB_KEY, 'query': name, 'include_adult': 'false'},
            timeout=15
        )
        r.raise_for_status()
        results = r.json().get('results', [])
        # Return first result with a profile photo
        for p in results[:3]:
            if p.get('profile_path'):
                return p
        return None
    except Exception as e:
        print(f'  Search error for {name}: {e}')
        return None

def download(url, dest):
    if os.path.exists(dest):
        return True
    try:
        r = requests.get(url, timeout=20, stream=True)
        if r.status_code == 404:
            return False
        r.raise_for_status()
        with open(dest, 'wb') as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return True
    except Exception as e:
        if os.path.exists(dest):
            os.remove(dest)
        return False

def actor_filename(name):
    """Convert actor name to safe filename."""
    return name.lower().strip()
    fname = re.sub(r'[^a-z0-9]+', '_', name.lower().strip())
    return fname.strip('_') + '.jpg'

def check_missing():
    """List guest images that are missing, empty, or possibly PNG saved as JPG."""
    print('='*60)
    print('CHECKING FOR MISSING/BROKEN GUEST IMAGES')
    print('='*60)
    if not os.path.exists(GUEST_DIR):
        print('Guest image folder does not exist yet — run without --check first')
        return

    broken = []
    png_as_jpg = []
    good = 0

    for fname in sorted(os.listdir(GUEST_DIR)):
        if not fname.endswith('.jpg'): continue
        path = os.path.join(GUEST_DIR, fname)
        size = os.path.getsize(path)
        if size < 1000:
            broken.append((fname, size, 'too small'))
            continue
        # Check actual file signature
        with open(path, 'rb') as f:
            header = f.read(8)
        # JPEG starts with FF D8
        if header[:2] == b'\xff\xd8':
            good += 1
        # PNG starts with 89 50 4E 47
        elif header[:4] == b'\x89PNG':
            png_as_jpg.append(fname)
        else:
            broken.append((fname, size, 'unknown format'))

    print(f'\nResults:')
    print(f'  Good JPEGs: {good}')

    if png_as_jpg:
        print(f'\n{len(png_as_jpg)} files are actually PNGs saved with .jpg extension:')
        for fname in png_as_jpg:
            print(f'  {fname}')
        print('  These display as broken images in the browser.')
        print('  Fix: rename them to .png OR replace with true JPEG versions.')

    if broken:
        print(f'\n{len(broken)} broken/empty files:')
        for fname, size, reason in broken:
            print(f'  {fname}  ({size} bytes — {reason})')

    if not png_as_jpg and not broken:
        print('\nAll guest images are valid JPEGs!')

    print('\nTotal files checked:', good + len(png_as_jpg) + len(broken))
    print('='*60)

def check_no_file():
    """Cross-reference guest list against downloaded files to find gaps."""
    print('='*60)
    print('GUESTS WITH NO IMAGE FILE')
    print('='*60)

    # Build guest map
    guest_map = {}
    for era_file in ERA_FILES:
        path = os.path.join(BASE, era_file)
        if not os.path.exists(path): continue
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        for ep in data.get('episodes', []):
            for g in (ep.get('guests') or []):
                actor = (g.get('actor') or '').strip()
                char  = (g.get('character') or '').strip()
                if not actor or actor in MAIN_CAST: continue
                if not char or char.lower() in ('voice','narrator','various'): continue
                if actor not in guest_map: guest_map[actor] = 0
                guest_map[actor] += 1

    guests_sorted = sorted(guest_map.items(), key=lambda x: x[1], reverse=True)

    missing = []
    for actor, count in guests_sorted:
        fname = re.sub(r'[^a-z0-9]+', '_', actor.lower().strip()).strip('_') + '.jpg'
        dest  = os.path.join(GUEST_DIR, fname)
        if not os.path.exists(dest):
            missing.append((actor, count, fname))

    if missing:
        print(f'\n{len(missing)} guests have no image file:')
        print(f'(sorted by appearance count)')
        print()
        for actor, count, fname in missing[:50]:  # Show top 50
            print(f'  {count:3d} eps  {actor:<35} → {fname}')
        if len(missing) > 50:
            for actor, count, fname in missing[50:]:
                print(f'  {count:3d} eps  {actor:<35} → {fname}')
    else:
        print('\nEvery guest has an image file!')
    print('='*60)

def retry_missing():
    """Retry downloading images for guests that have no file yet."""
    print('='*60)
    print('RETRYING MISSING GUEST IMAGES')
    print('='*60)

    guest_map = {}
    for era_file in ERA_FILES:
        path = os.path.join(BASE, era_file)
        if not os.path.exists(path): continue
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        for ep in data.get('episodes', []):
            for g in (ep.get('guests') or []):
                actor = (g.get('actor') or '').strip()
                char  = (g.get('character') or '').strip()
                if not actor or actor in MAIN_CAST: continue
                if not char or char.lower() in ('voice','narrator','various'): continue
                if actor not in guest_map: guest_map[actor] = 0
                guest_map[actor] += 1

    guests_sorted = sorted(guest_map.items(), key=lambda x: x[1], reverse=True)
    retried = downloaded = not_found = 0

    for actor, count in guests_sorted:
        fname = re.sub(r'[^a-z0-9]+', '_', actor.lower().strip()).strip('_') + '.jpg'
        dest  = os.path.join(GUEST_DIR, fname)
        if os.path.exists(dest): continue

        print(f'  {actor} ({count} ep{"s" if count!=1 else ""})...', end=' ', flush=True)
        retried += 1
        person = tmdb_search_person(actor)
        if not person or not person.get('profile_path'):
            print('no photo on TMDB')
            not_found += 1
            time.sleep(0.1)
            continue
        url = TMDB_IMG + person['profile_path']
        ok  = download(url, dest)
        if ok:
            print('✓')
            downloaded += 1
        else:
            print('download failed')
        time.sleep(0.25)

    print(f'\nRetry complete: {downloaded} new downloads, {not_found} not on TMDB')
    print('='*60)

def main():
    import sys
    if '--check' in sys.argv:
        check_missing()
        return
    if '--missing' in sys.argv:
        check_no_file()
        return
    if '--retry' in sys.argv:
        retry_missing()
        return
    print('='*60)
    print('SIMPSONS GUEST HEADSHOT DOWNLOADER')
    print('='*60)

    # Build guest map from all era files
    guest_map = {}
    for era_file in ERA_FILES:
        path = os.path.join(BASE, era_file)
        if not os.path.exists(path):
            print(f'Skipping {era_file} — not found')
            continue
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        for ep in data.get('episodes', []):
            for g in (ep.get('guests') or []):
                actor = (g.get('actor') or '').strip()
                if not actor or actor in MAIN_CAST:
                    continue
                char = (g.get('character') or '').strip()
                # Skip junk entries
                if not char or char.lower() in ('voice', 'narrator', 'various'):
                    continue
                if actor not in guest_map:
                    guest_map[actor] = 0
                guest_map[actor] += 1

    # Sort by appearances
    guests_sorted = sorted(guest_map.items(), key=lambda x: x[1], reverse=True)
    print(f'\nFound {len(guests_sorted)} unique guests')
    print(f'Downloading top guests by appearance count...\n')

    downloaded = 0
    skipped    = 0
    not_found  = 0
    errors     = 0

    for actor, count in guests_sorted:
        # Generate filename: lowercase, underscores
        fname = re.sub(r'[^a-z0-9]+', '_', actor.lower().strip()).strip('_') + '.jpg'
        dest  = os.path.join(GUEST_DIR, fname)

        if os.path.exists(dest):
            skipped += 1
            continue

        print(f'  {actor} ({count} ep{"s" if count!=1 else ""})...', end=' ', flush=True)

        person = tmdb_search_person(actor)
        if not person or not person.get('profile_path'):
            print('no photo found')
            not_found += 1
            time.sleep(0.1)
            continue

        url = TMDB_IMG + person['profile_path']
        ok  = download(url, dest)
        if ok:
            print('✓')
            downloaded += 1
        else:
            print('download failed')
            errors += 1

        time.sleep(0.2)  # polite to TMDB

    print(f'\n{"="*60}')
    print('DONE')
    print(f'  Downloaded:  {downloaded}')
    print(f'  Already had: {skipped}')
    print(f'  No photo:    {not_found}')
    print(f'  Errors:      {errors}')
    print(f'\nHeadshots saved to: {GUEST_DIR}')
    print('Hard refresh your browser to see the Hall of Fame montage!')
    print('='*60)

if __name__ == '__main__':
    main()
