#!/usr/bin/env python3
"""
MST3K TMDB Enrichment Script
==============================
Fetches all 10 seasons of Mystery Science Theater 3000 from TMDB,
parses movie titles and shorts from episode overviews, assigns hosts,
downloads episode stills, and builds the complete show JSON.

Run from the "TV Vault New Index and Json folders" directory.

Output:
  images/mst3k/          — episode stills + season posters + show images
  mst3k_data.json        — complete enriched show data
  mst3k_report.txt       — summary of what was found per episode
"""

import json, os, re, time, urllib.request, urllib.error, shutil
from pathlib import Path

TMDB_KEY      = '573382ec2121f69d6a89fce35293591a'
TMDB_STILL    = 'https://image.tmdb.org/t/p/w300'
TMDB_STILL_LG = 'https://image.tmdb.org/t/p/w780'
TMDB_POSTER   = 'https://image.tmdb.org/t/p/w500'
TMDB_BACKDROP = 'https://image.tmdb.org/t/p/w1280'
DELAY         = 0.22
SHOW_TMDB_ID  = 1952

IMG_DIR       = Path('images/mst3k')

# ── Host assignment by season ─────────────────────────────────────────────────
# Joel: S1-S5 (ep 1-512), Mike takes over mid S5 (ep 513 onwards)
# S6-S10: Mike
# Within S5: episodes 1-8 are Joel, ep 9+ is Mike (Joel leaves during ep 512)
SEASON_HOSTS = {
    1: 'Joel', 2: 'Joel', 3: 'Joel', 4: 'Joel',
    5: 'mixed',  # handled per-episode below
    6: 'Mike', 7: 'Mike', 8: 'Mike', 9: 'Mike', 10: 'Mike'
}
# S5 Joel episodes: 1-8, Mike: 9-13
S5_JOEL_EPS = set(range(1, 9))

SEASON_YEARS = {
    1: '1989-1990', 2: '1990-1991', 3: '1991-1992', 4: '1992-1993',
    5: '1993-1994', 6: '1994-1995', 7: '1995-1996', 8: '1996-1997',
    9: '1997-1998', 10: '1998-1999'
}

SEASON_NETWORKS = {
    1: 'Comedy Channel', 2: 'Comedy Channel', 3: 'Comedy Central',
    4: 'Comedy Central', 5: 'Comedy Central', 6: 'Comedy Central',
    7: 'Comedy Central', 8: 'Sci-Fi Channel', 9: 'Sci-Fi Channel',
    10: 'Sci-Fi Channel'
}

SEASON_TAGLINES = {
    1:  "Joel and the bots meet The Crawling Eye — the original run begins.",
    2:  "TV's Frank arrives and the riffing hits its stride.",
    3:  "Comedy Central era peaks — Pod People, Daddy-O, and Cave Dwellers.",
    4:  "Manos: The Hands of Fate. Enough said.",
    5:  "Joel says goodbye. Mike says hello. The bots carry on.",
    6:  "Mike's first full season — Samson vs. the Vampire Women and more.",
    7:  "The shortest season — six episodes and a feature film.",
    8:  "Sci-Fi Channel era begins — Pearl, Bobo, and Observer join the fray.",
    9:  "The long strange trip continues — Werewolf, Pumaman, and more.",
    10: "The classic run ends — Boggy Creek II and Girl in Gold Boots farewell."
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def safe_filename(name):
    name = re.sub(r'[^\w\-.]', '_', name.strip())
    return re.sub(r'_+', '_', name).strip('_')

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

def parse_movie_and_shorts(ep_name, overview):
    """
    Extract the main movie title and any shorts from TMDB episode data.
    TMDB episode titles for MST3K are usually the movie title directly.
    Shorts appear in the overview text.
    """
    # Episode title IS the movie title in MST3K TMDB entries
    movie = ep_name.strip() if ep_name else ''

    # Remove common prefixes TMDB sometimes adds
    for prefix in ['MST3K: ', 'Mystery Science Theater: ']:
        if movie.startswith(prefix):
            movie = movie[len(prefix):]

    # Parse shorts from overview
    # TMDB often lists them as: "Short: X" or mentions them in the description
    shorts = []

    if overview:
        # Pattern 1: "short [titled/called/named] X" 
        short_patterns = [
            r'short(?:s)?[:\s]+["\']?([^\.,"\']+)["\']?',
            r'preceded by[:\s]+["\']?([^\.,"\']+)["\']?',
            r'with short[:\s]+["\']?([^\.,"\']+)["\']?',
            r'"([^"]+)"[,\s]+a short',
            r'short film[:\s]+["\']?([^\.,"\']+)["\']?',
        ]

        for pattern in short_patterns:
            matches = re.findall(pattern, overview, re.IGNORECASE)
            for m in matches:
                short = m.strip().strip('"\'').strip()
                # Filter out junk matches
                if len(short) > 3 and len(short) < 80 and short not in shorts:
                    # Clean up trailing punctuation
                    short = re.sub(r'[,\.]+$', '', short).strip()
                    shorts.append(short)

        # Pattern 2: Look for quoted titles near "short" keyword in overview
        # e.g. 'The short "Truck Farmer" precedes...'
        quoted = re.findall(r'"([^"]{3,60})"', overview)
        for q in quoted:
            if any(word in overview[overview.find(q)-50:overview.find(q)].lower()
                   for word in ['short', 'preceded', 'preced']):
                if q not in shorts:
                    shorts.append(q)

    return movie, shorts

def get_host(season_num, ep_num):
    if SEASON_HOSTS.get(season_num) == 'mixed':
        return 'Joel' if ep_num in S5_JOEL_EPS else 'Mike'
    return SEASON_HOSTS.get(season_num, 'Joel')

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("MST3K TMDB Enrichment Script")
    print("=" * 50)

    IMG_DIR.mkdir(parents=True, exist_ok=True)

    report = []
    seasons_data = []

    # Fetch show-level info
    print("\nFetching show info...")
    show_info = tmdb_api(f'/tv/{SHOW_TMDB_ID}')
    time.sleep(DELAY)

    show_backdrop = './images/shows/Mystery_Science_Theater_3000_backdrop.jpg'
    show_poster   = './images/shows/Mystery_Science_Theater_3000_poster.jpg'

    if show_info:
        print(f"  Show: {show_info.get('name')}")
        print(f"  Seasons on TMDB: {show_info.get('number_of_seasons')}")
        print(f"  Total episodes: {show_info.get('number_of_episodes')}")

    # Process seasons 1-10
    for season_num in range(1, 11):
        print(f"\n── Season {season_num} ({SEASON_YEARS[season_num]}) ────────────")
        season_data = tmdb_api(f'/tv/{SHOW_TMDB_ID}/season/{season_num}')
        time.sleep(DELAY)

        # Download season poster
        season_poster = ''
        if season_data and season_data.get('poster_path'):
            url = TMDB_POSTER + season_data['poster_path']
            dest = IMG_DIR / f'season_{season_num}_poster.jpg'
            if download(url, dest, f'S{season_num} poster'):
                season_poster = f'./images/mst3k/season_{season_num}_poster.jpg'
            time.sleep(DELAY)

        # Download season backdrop if available
        season_backdrop = ''
        if season_data and season_data.get('poster_path'):
            # Use first episode backdrop as season backdrop
            pass

        tmdb_episodes = {}
        if season_data and season_data.get('episodes'):
            for ep in season_data['episodes']:
                tmdb_episodes[ep['episode_number']] = ep
            print(f"  TMDB returned {len(tmdb_episodes)} episodes")
        else:
            print(f"  No TMDB data for season {season_num}")

        episodes = []
        for ep_num in sorted(tmdb_episodes.keys()):
            tmdb_ep = tmdb_episodes[ep_num]

            ep_name    = tmdb_ep.get('name', f'Episode {ep_num}')
            overview   = tmdb_ep.get('overview', '')
            airdate    = tmdb_ep.get('air_date', '')
            still_path = tmdb_ep.get('still_path', '')
            host       = get_host(season_num, ep_num)

            # Parse movie title and shorts
            movie, shorts = parse_movie_and_shorts(ep_name, overview)

            # Download episode still
            still_local = ''
            if still_path:
                filename = f's{season_num}e{ep_num:02d}_still.jpg'
                dest = IMG_DIR / filename
                url = TMDB_STILL_LG + still_path
                if download(url, dest, f'S{season_num}E{ep_num}'):
                    still_local = f'./images/mst3k/{filename}'
                time.sleep(DELAY)

            ep_entry = {
                'num':       ep_num,
                'title':     movie,
                'host':      host,
                'airdate':   airdate,
                'shorts':    shorts,
                'has_short': len(shorts) > 0,
                'desc':      overview,
                'still':     still_local,
            }
            episodes.append(ep_entry)

            has_still = '✓' if still_local else '✗'
            has_short = f"short={shorts[0][:30]}" if shorts else 'no short'
            print(f"  S{season_num}E{ep_num:02d} [{host}] {movie[:35]:<35} still={has_still} {has_short}")
            report.append(
                f"S{season_num}E{ep_num:02d} | host={host} | movie={movie} | "
                f"shorts={', '.join(shorts) if shorts else 'none'} | "
                f"still={'YES' if still_local else 'NO'}"
            )

        seasons_data.append({
            'num':      season_num,
            'year':     SEASON_YEARS[season_num],
            'network':  SEASON_NETWORKS[season_num],
            'tagline':  SEASON_TAGLINES[season_num],
            'poster':   season_poster,
            'episodes': episodes,
        })

    # Build complete show entry
    mst3k = {
        "id":          "mystery-science-theater-3000",
        "title":       "Mystery Science Theater 3000",
        "category":    "Comedy",
        "network":     "Comedy Channel / Comedy Central / Sci-Fi Channel",
        "years":       "1989-1999",
        "collectionNote": "",
        "tmdbId":      SHOW_TMDB_ID,
        "stars":       ["Joel Hodgson", "Michael J. Nelson"],
        "description": "A stranded test subject and his robot companions survive a blitz of cheesy B-movies by riffing on them with wit, sarcasm, and pure comedic genius. Ten seasons, hundreds of terrible films, and one of the greatest comedy shows ever made.",
        "cast": [
            {"actor": "Joel Hodgson",      "character": "Joel Robinson (Seasons 1-5)"},
            {"actor": "Michael J. Nelson", "character": "Mike Nelson (Seasons 5-10)"},
            {"actor": "Trace Beaulieu",    "character": "Crow T. Robot / Dr. Clayton Forrester"},
            {"actor": "Kevin Murphy",      "character": "Tom Servo"},
            {"actor": "Frank Conniff",     "character": "TV's Frank"},
            {"actor": "Mary Jo Pehl",      "character": "Pearl Forrester"},
            {"actor": "Bill Corbett",      "character": "Crow T. Robot (Seasons 8-10)"},
        ],
        "seasons":      seasons_data,
        "localPoster":  show_poster,
        "localBackdrop": show_backdrop,
    }

    # Save
    with open('mst3k_data.json', 'w') as f:
        json.dump(mst3k, f, separators=(',', ':'), ensure_ascii=False)
    print(f"\n✓ mst3k_data.json saved")

    with open('mst3k_report.txt', 'w') as f:
        f.write('\n'.join(report))
    print(f"✓ mst3k_report.txt saved")

    # Summary
    total_eps    = sum(len(s['episodes']) for s in seasons_data)
    total_stills = sum(1 for s in seasons_data for e in s['episodes'] if e.get('still'))
    total_shorts = sum(1 for s in seasons_data for e in s['episodes'] if e.get('has_short'))
    joel_eps     = sum(1 for s in seasons_data for e in s['episodes'] if e.get('host') == 'Joel')
    mike_eps     = sum(1 for s in seasons_data for e in s['episodes'] if e.get('host') == 'Mike')
    img_count    = len(list(IMG_DIR.iterdir()))

    print(f"\n=== DONE ===")
    print(f"  Total episodes:  {total_eps}")
    print(f"  Joel episodes:   {joel_eps}")
    print(f"  Mike episodes:   {mike_eps}")
    print(f"  With stills:     {total_stills}/{total_eps}")
    print(f"  With shorts:     {total_shorts}/{total_eps}")
    print(f"  Images saved:    {img_count}")
    print(f"\nNext: upload mst3k_data.json + mst3k_report.txt to Claude to build the hub.")

if __name__ == '__main__':
    main()
