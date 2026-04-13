#!/usr/bin/env python3
"""
Gray Video Vault — Image Self-Hosting Script
=============================================
Downloads all remote images and updates JSON files to use local paths.

Run from the "TV Vault New Index and Json folders" directory.

Creates:
  images/characters/   — 40 LT character card images
  images/posters/      — 713 LT cartoon posters
  images/backdrops/    — 643 LT cartoon backdrops
  images/shows/        — poster + backdrop for each show with TMDB ID
  images/artists/      — profile photo for each artist

Updates (in place, backups saved):
  looney_tunes_characters.json
  looney_tunes_enriched_final.json
  shows_data.json
  artists_data.json
"""

import json, os, re, time, urllib.request, urllib.error, shutil
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
TMDB_KEY      = '573382ec2121f69d6a89fce35293591a'
TMDB_POSTER   = 'https://image.tmdb.org/t/p/w500'
TMDB_LARGE    = 'https://image.tmdb.org/t/p/w780'
TMDB_BACKDROP = 'https://image.tmdb.org/t/p/w1280'
TMDB_PROFILE  = 'https://image.tmdb.org/t/p/w300'
DELAY         = 0.2   # seconds between downloads

IMG_DIR       = Path('images')
CHARS_DIR     = IMG_DIR / 'characters'
POSTERS_DIR   = IMG_DIR / 'posters'
BACKDROPS_DIR = IMG_DIR / 'backdrops'
SHOWS_DIR     = IMG_DIR / 'shows'
ARTISTS_DIR   = IMG_DIR / 'artists'

# ── Helpers ───────────────────────────────────────────────────────────────────

def make_dirs():
    for d in [CHARS_DIR, POSTERS_DIR, BACKDROPS_DIR, SHOWS_DIR, ARTISTS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

def safe_filename(name):
    """Convert a string to a safe filename."""
    name = re.sub(r'[^\w\-.]', '_', name.strip())
    return re.sub(r'_+', '_', name).strip('_')

def download(url, dest_path, label=''):
    """Download url to dest_path. Returns True on success."""
    if dest_path.exists():
        return True  # already downloaded
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read()
        if len(data) < 500:  # probably an error page
            return False
        dest_path.write_bytes(data)
        return True
    except Exception as e:
        print(f"  FAIL {label}: {e}")
        return False

def tmdb_api(path):
    """Call TMDB API, return parsed JSON or None."""
    url = f"https://api.themoviedb.org/3{path}?api_key={TMDB_KEY}"
    try:
        with urllib.request.urlopen(url, timeout=12) as r:
            return json.loads(r.read())
    except:
        return None

def ext_from_url(url):
    """Get file extension from URL."""
    path = url.split('?')[0].split('#')[0]
    ext = os.path.splitext(path)[1].lower()
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']:
        return ext
    return '.jpg'

# ── Section 1: LT Character Images ───────────────────────────────────────────

def download_character_images(chars_data):
    print("\n── LT CHARACTER IMAGES ──────────────────────────────────────")
    ok, fail = 0, 0
    for char in chars_data['characters']:
        img_url = char.get('image_url', '')
        if not img_url:
            print(f"  SKIP (no url): {char['name']}")
            continue

        ext = ext_from_url(img_url)
        filename = safe_filename(char['id']) + ext
        dest = CHARS_DIR / filename
        local_path = f'./images/characters/{filename}'

        if download(img_url, dest, char['name']):
            char['image_url'] = local_path
            ok += 1
            print(f"  ✓ {char['name']}")
        else:
            fail += 1
            print(f"  ✗ {char['name']} — keeping remote URL")
        time.sleep(DELAY)

    print(f"  Done: {ok} ok, {fail} failed")
    return chars_data

# ── Section 2: LT Cartoon Posters & Backdrops ────────────────────────────────

def download_lt_images(lt_data):
    print("\n── LT POSTERS & BACKDROPS ───────────────────────────────────")
    poster_ok, poster_fail = 0, 0
    backdrop_ok, backdrop_fail = 0, 0

    for decade_key, decade_data in lt_data['by_decade'].items():
        cartoons = decade_data if isinstance(decade_data, list) else decade_data.get('cartoons', [])
        for c in cartoons:
            title_safe = safe_filename(c.get('title', 'unknown'))
            year = c.get('year', '')

            # Poster
            poster = c.get('poster', '')
            if poster:
                if poster.startswith('http'):
                    # Already a full URL (the 12 hardcoded ones)
                    ext = ext_from_url(poster)
                    filename = f"{title_safe}_{year}_poster{ext}"
                    url = poster
                else:
                    ext = ext_from_url(poster)
                    filename = f"{title_safe}_{year}_poster{ext}"
                    url = TMDB_LARGE + poster

                dest = POSTERS_DIR / filename
                if download(url, dest):
                    c['poster'] = f'./images/posters/{filename}'
                    poster_ok += 1
                else:
                    poster_fail += 1
                time.sleep(DELAY)

            # Backdrop
            backdrop = c.get('backdrop', '')
            if backdrop:
                if backdrop.startswith('http'):
                    ext = ext_from_url(backdrop)
                    filename = f"{title_safe}_{year}_backdrop{ext}"
                    url = backdrop
                else:
                    ext = ext_from_url(backdrop)
                    filename = f"{title_safe}_{year}_backdrop{ext}"
                    url = TMDB_BACKDROP + backdrop

                dest = BACKDROPS_DIR / filename
                if download(url, dest):
                    c['backdrop'] = f'./images/backdrops/{filename}'
                    backdrop_ok += 1
                else:
                    backdrop_fail += 1
                time.sleep(DELAY)

    print(f"  Posters: {poster_ok} ok, {poster_fail} failed")
    print(f"  Backdrops: {backdrop_ok} ok, {backdrop_fail} failed")
    return lt_data

# ── Section 3: Show Posters & Backdrops ──────────────────────────────────────

def download_show_images(shows):
    print("\n── SHOW POSTERS & BACKDROPS ─────────────────────────────────")
    ok, fail, skip = 0, 0, 0

    for s in shows:
        tmdb_id = s.get('tmdbId')
        title_safe = safe_filename(s.get('title', s.get('id', 'unknown')))

        if not tmdb_id:
            skip += 1
            continue

        # Fetch show details from TMDB
        info = tmdb_api(f'/tv/{tmdb_id}')
        time.sleep(DELAY)

        if not info:
            fail += 1
            continue

        # Poster
        poster_path = info.get('poster_path', '')
        if poster_path:
            filename = f"{title_safe}_poster.jpg"
            dest = SHOWS_DIR / filename
            url = TMDB_LARGE + poster_path
            if download(url, dest, s['title']):
                s['localPoster'] = f'./images/shows/{filename}'
                ok += 1
            else:
                fail += 1
            time.sleep(DELAY)

        # Backdrop
        backdrop_path = info.get('backdrop_path', '')
        if backdrop_path:
            filename = f"{title_safe}_backdrop.jpg"
            dest = SHOWS_DIR / filename
            url = TMDB_BACKDROP + backdrop_path
            if download(url, dest, s['title']):
                s['localBackdrop'] = f'./images/shows/{filename}'
            time.sleep(DELAY)

    print(f"  Done: {ok} ok, {fail} failed, {skip} skipped (no TMDB ID)")
    return shows

# ── Section 4: Artist Images ──────────────────────────────────────────────────

def download_artist_images(artists):
    print("\n── ARTIST IMAGES ────────────────────────────────────────────")
    ok, fail = 0, 0

    for a in artists:
        tmdb_person_id = a.get('tmdbPersonId')
        name_safe = safe_filename(a.get('name', a.get('id', 'unknown')))

        if not tmdb_person_id:
            print(f"  SKIP (no TMDB person ID): {a.get('name')}")
            fail += 1
            continue

        # Fetch person details
        info = tmdb_api(f'/person/{tmdb_person_id}')
        time.sleep(DELAY)

        if not info:
            fail += 1
            continue

        profile_path = info.get('profile_path', '')
        if profile_path:
            filename = f"{name_safe}_profile.jpg"
            dest = ARTISTS_DIR / filename
            url = TMDB_PROFILE + profile_path
            if download(url, dest, a['name']):
                a['localImage'] = f'./images/artists/{filename}'
                ok += 1
                print(f"  ✓ {a['name']}")
            else:
                fail += 1
        time.sleep(DELAY)

        # Also fetch backdrop if customBackdrop is set
        custom = a.get('customBackdrop', '')
        if custom and custom.startswith('http'):
            ext = ext_from_url(custom)
            filename = f"{name_safe}_backdrop{ext}"
            dest = ARTISTS_DIR / filename
            if download(custom, dest, a['name'] + ' backdrop'):
                a['localBackdrop'] = f'./images/artists/{filename}'
            time.sleep(DELAY)

    print(f"  Done: {ok} ok, {fail} failed")
    return artists

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Gray Video Vault — Image Download Script")
    print("=" * 50)

    # Check we're in the right folder
    required = ['looney_tunes_characters.json', 'looney_tunes_enriched_final.json',
                'shows_data.json', 'artists_data.json']
    for f in required:
        if not Path(f).exists():
            print(f"ERROR: {f} not found. Run this script from the 'TV Vault New Index and Json folders' directory.")
            return

    make_dirs()
    print(f"Images folder: {IMG_DIR.resolve()}")

    # Load all JSON files
    print("\nLoading JSON files...")
    with open('looney_tunes_characters.json') as f:
        chars_data = json.load(f)
    with open('looney_tunes_enriched_final.json') as f:
        lt_data = json.load(f)
    with open('shows_data.json') as f:
        shows = json.load(f)
    with open('artists_data.json') as f:
        artists = json.load(f)

    # Backups
    for fname in required:
        shutil.copy(fname, fname.replace('.json', '.BACKUP.json'))
    print("Backups saved.")

    # Run all downloads
    chars_data = download_character_images(chars_data)
    lt_data    = download_lt_images(lt_data)
    shows      = download_show_images(shows)
    artists    = download_artist_images(artists)

    # Save all updated JSON files
    print("\nSaving updated JSON files...")
    with open('looney_tunes_characters.json', 'w') as f:
        json.dump(chars_data, f, separators=(',', ':'), ensure_ascii=False)
    with open('looney_tunes_enriched_final.json', 'w') as f:
        json.dump(lt_data, f, separators=(',', ':'), ensure_ascii=False)
    with open('shows_data.json', 'w') as f:
        json.dump(shows, f, separators=(',', ':'), ensure_ascii=False)
    with open('artists_data.json', 'w') as f:
        json.dump(artists, f, separators=(',', ':'), ensure_ascii=False)

    # Count downloaded files
    total = sum(len(list(d.iterdir())) for d in [CHARS_DIR, POSTERS_DIR, BACKDROPS_DIR, SHOWS_DIR, ARTISTS_DIR])
    print(f"\n✓ DONE — {total} images downloaded")
    print(f"  characters: {len(list(CHARS_DIR.iterdir()))}")
    print(f"  posters:    {len(list(POSTERS_DIR.iterdir()))}")
    print(f"  backdrops:  {len(list(BACKDROPS_DIR.iterdir()))}")
    print(f"  shows:      {len(list(SHOWS_DIR.iterdir()))}")
    print(f"  artists:    {len(list(ARTISTS_DIR.iterdir()))}")
    print("\nAll JSON files updated with local paths.")
    print("Deploy the entire 'TV Vault New Index and Json folders' to Netlify.")

if __name__ == '__main__':
    main()
