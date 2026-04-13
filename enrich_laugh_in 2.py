#!/usr/bin/env python3
"""
Laugh-In TMDB Enrichment Script
=================================
Fetches episode stills, overviews, and guest stars from TMDB for all 6 seasons
of Rowan & Martin's Laugh-In (TMDB ID: 9895), merges with epguides guest data,
downloads all episode still images, and builds the complete show JSON entry.

Run from the "TV Vault New Index and Json folders" directory.

Output:
  images/laugh_in/          — episode stills + show images
  laugh_in_data.json        — complete enriched show data
  laugh_in_report.txt       — summary of what TMDB had
"""

import json, os, re, time, urllib.request, urllib.error, shutil
from pathlib import Path

TMDB_KEY      = '573382ec2121f69d6a89fce35293591a'
TMDB_STILL    = 'https://image.tmdb.org/t/p/w300'
TMDB_STILL_LG = 'https://image.tmdb.org/t/p/w780'
TMDB_POSTER   = 'https://image.tmdb.org/t/p/w500'
TMDB_BACKDROP = 'https://image.tmdb.org/t/p/w1280'
DELAY         = 0.22
SHOW_TMDB_ID  = 9895

IMG_DIR       = Path('images/laugh_in')

# ── Complete epguides guest data (source of truth for guests) ─────────────────
EPGUIDES_DATA = {
    # (season, ep): [guests]
    (1,1):  ["Leo G. Carroll","Barbara Feldon","Lorne Greene","Buddy Hackett","Sheldon Leonard","The Strawberry Alarm Clock","Tiny Tim","Flip Wilson"],
    (1,2):  ["Leo G. Carroll","Robert Culp","The First Edition","Larry Hovis","Sheldon Leonard","Tom Smothers","Flip Wilson","Muriel Landers"],
    (1,3):  ["Tim Conway","Cher","Sheldon Leonard","Tiny Tim","Flip Wilson","Paul Gilbert"],
    (1,4):  ["Don Adams","Douglas Fairbanks Jr.","Nitty Gritty Dirt Band","Jack Riley","Walter Slezak","David Watson","Pamela Austin","Paul Gilbert"],
    (1,5):  ["Kaye Ballard","Richard Dawson","Douglas Fairbanks Jr.","Larry Hovis","Peter Lawford","Dinah Shore","Walter Slezak"],
    (1,6):  ["Nancy Ames","Buddy Hackett","Jerry Lewis","Leonard Nimoy","Edward Platt","Connie Stevens","Larry Storch","The Temptations"],
    (1,7):  ["Godfrey Cambridge","Sally Field","Larry Hovis","Jerry Lewis","Terry-Thomas","Joby Baker","Inga Neilsen"],
    (1,8):  ["Barbara Feldon","Anissa Jones","Jerry Lewis","Pat Morita","Dinah Shore","Sonny & Cher","John Wayne","Paul Winchell"],
    (1,9):  ["Elgin Baylor","Harry Belafonte","Joey Bishop","Sammy Davis Jr.","Regis Philbin","John Wayne","Pamela Austin"],
    (1,10): ["The Bee Gees","Johnny Carson","Barbara Feldon","Harry Belafonte","Ed McMahon","Flip Wilson","Sivi Aberg"],
    (1,11): ["John Byner","Hugh Downs","James Garner","Flip Wilson","Paul Winchell","Pamela Austin","David Lipp"],
    (1,12): ["Kaye Ballard","Harry Belafonte","Shelley Berman","John Byner","James Garner","John Wayne","Flip Wilson","The Curtain Callers"],
    (1,13): ["Shelley Berman","John Byner","Johnny Carson","Tim Conway","Hugh Downs","Barbara Feldon","John Wayne","Flip Wilson","Paul Winchell"],
    (1,14): ["Milton Berle","Shelley Berman","Joey Bishop","John Byner","Jill St. John","Tiny Tim","John Wayne","Flip Wilson","Sivi Aberg","Pamela Austin"],
    (2,1):  ["Zsa Zsa Gabor","Hugh Hefner","Bob Hope","Jack Lemmon","Richard Nixon","Sonny Tufts","John Wayne","John B. Whitney"],
    (2,2):  ["Herb Alpert","Eve Arden","Arlene Dahl","Zsa Zsa Gabor","George Kirby","Jack Lemmon","John Wayne","Patrick Wayne"],
    (2,3):  ["Zsa Zsa Gabor","Greer Garson","Bob Hope","Abbe Lane","Greg Morris","Otto Preminger"],
    (2,4):  ["Robert Culp","Arlene Dahl","Kirk Douglas","Lena Horne","Liberace","France Nuyen","Otto Preminger","Sonny Tufts","Flip Wilson","Catherine Reid"],
    (2,5):  ["Bobby Darin","Holy Modal Rounders","Rosemary Clooney","Kirk Douglas","Mitzi Gaynor","Harland Sanders","Sonny Tufts"],
    (2,6):  ["Greer Garson","Van Johnson","Werner Klemperer","Liberace","Flip Wilson"],
    (2,7):  ["Bill Dana","Jimmy Dean","Zsa Zsa Gabor","Lena Horne","Marcel Marceau","Sonny Tufts"],
    (2,8):  ["George Gobel","Dick Gregory","Rock Hudson","Rod Serling"],
    (2,9):  ["Victor Borge","Rosemary Clooney","Arlene Dahl","George Gobel","Phil Harris","George Kirby"],
    (2,10): ["Perry Como","Joseph Cotten","Arlene Dahl","Phyllis Diller","Zsa Zsa Gabor","Otto Preminger","Vincent Price","Tiny Tim","Henny Youngman"],
    (2,11): ["Joseph Cotten","Tony Curtis","Peter Lawford","Liberace","Cliff Robertson","Henny Youngman"],
    (2,12): ["Barbara Bain","Billy Barty","Jack Benny","Douglas Fairbanks Jr.","Rock Hudson","Martin Landau","Guy Lombardo","Otto Preminger"],
    (2,13): ["Sally Field","Rich Little","Vincent Price","Don Rickles","Bill Dana","Nanette Fabray","Lena Horne","George Jessel","Bob Newhart","Kate Smith"],
    (2,14): ["Jack Benny","Peter Falk","Marcel Marceau","Garry Moore","Flip Wilson","Henry Youngman"],
    (2,15): ["Peter Lawford","Johnny Carson","Perry Como","David Janssen","Van Johnson"],
    (2,16): ["George Gobel","Guy Lombardo","Pat Nixon","Richard Nixon","Nancy Sinatra","Smothers Brothers"],
    (2,17): ["Jack Benny","Tony Curtis","Zsa Zsa Gabor","Frank Gorshin","George Jessel","Janos Prohaska","Samantha Lloyd"],
    (2,18): ["George Jessel","Tom Kennedy","Liberace","Rich Little","Don Rickles","Cliff Robertson","John Roach"],
    (2,19): ["Greer Garson","Davy Jones","Nipsey Russell","Robert Wagner","Al 'Red Dog' Weber"],
    (2,20): ["Jack Benny","James Drury","James Garner","Guy Lombardo","Gina Lollobrigida","Doug McClure","Tiny Tim"],
    (2,21): ["Mel Brooks","Peter Falk","Lena Horne","Rock Hudson","Peter Lawford","Bob Newhart","Connie Stevens","Tiny Tim"],
    (2,22): ["Tony Curtis","Ann Miller","Smothers Brothers","James Garner","Forrest Tucker","Robert Wagner","Shelley Winters"],
    (2,23): ["James Drury","Werner Klemperer","Gina Lollobrigida","Doug McClure","Connie Stevens","Flip Wilson"],
    (2,24): ["Tony Curtis","Werner Klemperer","Ann Miller","Garry Moore","Flip Wilson"],
    (2,25): ["Tony Curtis","Perry Como","Laurence Harvey","Flip Wilson","Stu Gilliam"],
    (2,26): ["George Gobel","Billy Graham","Werner Klemperer","Richard Nixon","Tiny Tim","Harry Wiere","Herbert Wiere","Sylvester Wiere"],
    (3,1):  ["Johnny Carson","Debbie Reynolds","Peter Sellers","Flip Wilson"],
    (3,2):  ["Michael Caine","Bob Hope","Diana Ross"],
    (3,3):  ["Sonny & Cher","Flip Wilson"],
    (3,4):  ["Micky Dolenz","Davy Jones","Mike Nesmith","The Monkees"],
    (3,5):  ["Mitzi Gaynor","Jack E. Leonard","Lana Wood"],
    (3,6):  ["Anne Jackson","Romy Schneider","Eli Wallach"],
    (3,7):  ["Sammy Davis Jr.","Jack Riley"],
    (3,8):  ["Sammy Davis Jr.","Buddy Hackett"],
    (3,9):  ["Johnny Carson","Carol Channing"],
    (3,10): ["Sid Caesar","Zsa Zsa Gabor","Diana Ross","Peter Sellers"],
    (3,11): ["Michael Caine","Tennessee Ernie Ford","Debbie Reynolds"],
    (3,12): ["Jack Benny","Johnny Carson","Zsa Zsa Gabor","Engelbert Humperdinck","Jill St. John","Peter Lawford"],
    (3,13): ["Phyllis Diller","Roger Moore","Romy Schneider","Jacqueline Susann"],
    (3,14): ["Sammy Davis Jr.","Greer Garson","Lorne Greene"],
    (3,15): ["George Gobel","Guy Lombardo","Ed McMahon","Frank Sinatra Jr.","Nancy Sinatra"],
    (3,16): ["James Garner","Engelbert Humperdinck","Roger Moore"],
    (3,17): ["Peter Wintonick","Jonathan Winters"],
    (3,18): ["Bing Crosby","Sammy Davis Jr.","Peter Lawford","Ed McMahon"],
    (3,19): ["Jack Benny","Tony Curtis","Tennessee Ernie Ford","Jill St. John"],
    (3,20): ["Jack Benny","Michael Caine","Johnny Carson","George Lindsey"],
    (3,21): ["Jim Backus","Greer Garson","Andy Williams","Andy Griffith","Carl Reiner"],
    (3,22): ["Dan Blocker","Perry Como","Tom Smothers","Flip Wilson"],
    (3,23): ["Carol Channing","Wally Cox","Sheldon Leonard","Ringo Starr"],
    (3,24): ["Danny Kaye","Zsa Zsa Gabor"],
    (3,25): ["Buddy Hackett","Billy Barnes","Edgar Bergen","Mickey Rooney","Nancy Sinatra","Jill St. John","Andy Williams","Agatha Grunt"],
    (3,26): ["Tony Curtis","Peter Sellers","Tiny Tim"],
    (4,1):  ["Art Carney","Jilly Rizzo"],
    (4,2):  ["David Frost","Don Rickles","Jilly Rizzo"],
    (4,3):  ["Carol Channing","Tim Conway","Goldie Hawn","Jilly Rizzo"],
    (4,4):  ["Ken Berry","Tim Conway","Jilly Rizzo"],
    (4,5):  ["Tim Conway","Jilly Rizzo"],
    (4,6):  ["David Frost","Don Ho","Zero Mostel"],
    (4,7):  ["Vincent Price","Rod Serling","Orson Welles"],
    (4,8):  ["Carol Channing"],
    (4,9):  ["Jim Backus","Greer Garson","Andy Griffith","Carl Reiner"],
    (4,10): ["Bob Newhart"],
    (4,11): ["Desi Arnaz"],
    (4,12): ["Peter Lawford","Ricardo Montalban","Vincent Price","Dinah Shore"],
    (4,13): ["Don Ho","Jilly Rizzo","Rod Serling","Phil Silvers"],
    (4,14): ["Bing Crosby","Phyllis Diller","Rich Little","Debbie Reynolds","Jilly Rizzo"],
    (4,15): ["William F. Buckley Jr.","Rich Little"],
    (4,16): ["Wilt Chamberlain","Sammy Davis Jr."],
    (4,17): ["Johnny Carson","Gore Vidal","Sam Yorty"],
    (4,18): ["Joey Bishop","Jilly Rizzo","David Steinberg"],
    (4,19): ["Jack Cassidy","Wilt Chamberlain","Teresa Graves","Andy Griffith"],
    (4,20): ["Teresa Graves","Marcello Mastroianni"],
    (4,21): ["Herschel Bernardi","Truman Capote","Wilt Chamberlain","Chuck Connors","Peter Lawford","Ricardo Montalban","Dinah Shore"],
    (4,22): ["Dinah Shore"],
    (4,23): ["Bing Crosby","Sammy Davis Jr.","Peter Lawford"],
    (4,24): ["Richard Crenna"],
    (4,25): ["Sammy Davis Jr."],
    (4,26): ["Fernando Lamas","Dinah Shore"],
    (5,1):  ["Johnny Carson","Bob Hope","Buffalo Bob Smith","Raquel Welch","Kent McCord","Martin Milner","Henny Youngman","Martha Mitchell"],
    (5,2):  ["Vida Blue","Roman Gabriel","Andy Granatelli","Joe Namath","Sugar Ray Robinson","Bill Russell","Doug Sanders","Vin Scully","Willie Shoemaker"],
    (5,3):  ["James Brolin","Rita Hayworth","Doc Severinsen","Henny Youngman"],
    (5,4):  ["Karen Valentine"],
    (5,5):  ["Tony Curtis","Frank Gorshin","Edward G. Robinson"],
    (5,6):  ["Richard Crenna","Janet Leigh"],
    (5,7):  ["Lee Grant","Jill St. John","Willie Shoemaker"],
    (5,8):  ["Teresa Graves","Tiny Tim","John Wayne","Jo Anne Worley"],
    (5,9):  ["Ralph Edwards","Jill St. John","Liza Minnelli","Edward G. Robinson"],
    (5,10): ["James Coco"],
    (5,11): ["Sheldon Leonard","Mike Mazurki","Agnes Moorehead","Vincent Price","Jack Soo"],
    (5,12): ["Bing Crosby","Janet Leigh","Carroll O'Connor"],
    (5,13): ["Charo","Petula Clark","Burt Mustin","Joe Namath","Queenie Smith"],
    (5,14): ["Fannie Flagg","Buddy Hackett","Jack LaLanne","Sally Struthers","Mona Tera"],
    (5,15): ["Robert Goulet","Larry Hovis","Tiny Tim"],
    (5,16): ["James Coco","Fannie Flagg","Charles Nelson Reilly","Mort Sahl","Henny Youngman"],
    (5,17): ["Sue Ane Langdon","Carl Reiner","Slappy White"],
    (5,18): ["Jack Carter","Chad Everett","Paul Lynde","John Wayne"],
    (5,19): ["Charlie Callas","Dick Cavett","Carol Channing","Richard Crenna","Slappy White"],
    (5,20): ["Johnny Cash","Sandy Duncan","Paul Lynde","Terry-Thomas"],
    (5,21): ["Robert Goulet","Gene Hackman","Sue Ane Langdon"],
    (5,22): ["Charlie Callas","Jack Carter","Johnny Cash","Dick Cavett","Burt Mustin","Debbie Reynolds","Queenie Smith"],
    (5,23): ["Steve Allen","Carol Channing","Gene Hackman","Jo Ann Pflug","Charles Nelson Reilly","Terry-Thomas","John Wayne"],
    (5,24): ["Vida Blue","Sandy Duncan","Roman Gabriel","Joe Namath","Jo Ann Pflug","Charles Nelson Reilly","Sugar Ray Robinson","Bill Russell","Doug Sanders","Willie Shoemaker","Jean Stapleton"],
    (6,1):  ["Isaac Hayes","Kent McCord","Martin Milner","Jill St. John","John Wayne"],
    (6,2):  ["Sebastian Cabot","Dyan Cannon","Janet Leigh","Julie London"],
    (6,3):  ["William Conrad","Bob Crane","Nanette Fabray","Henry Mancini"],
    (6,4):  ["Lucie Arnaz","Rich Little","Ross Martin"],
    (6,5):  ["Steve Allen","Mama Cass Elliott","Michael Landon","Della Reese","Henny Youngman"],
    (6,6):  ["Jack Benny","James Farentino","Michele Lee","Peter Marshall","Hugh O'Brian","Charles Nelson Reilly"],
    (6,7):  ["Bill Bixby","Jack Carter","Jean Stapleton","Henny Youngman"],
    (6,8):  ["Mike Connors","Totie Fields","Charles Nelson Reilly"],
    (6,9):  ["Jack Benny","Sue Ane Langdon","Sally Struthers"],
    (6,10): ["James Caan","Bob Crane","Nanette Fabray","Della Reese"],
    (6,11): ["Carol Burnett","Ross Martin","Demond Wilson","Paul Gilbert"],
    (6,12): ["Jack Klugman","Rich Little","Henny Youngman"],
    (6,13): ["Steve Allen","Steve Lawrence","Peter Marshall"],
    (6,14): ["Howard Cosell","Alex Karras","Kent McCord","Martin Milner","Vin Scully"],
    (6,15): ["Charlie Callas","Kent McCord","Martin Milner","Don Rickles"],
    (6,16): ["Robert Goulet"],
    (6,17): ["Sammy Davis Jr."],
    (6,18): ["Angie Dickinson","Totie Fields","Monty Hall"],
    (6,19): ["Phyllis Diller","Oral Roberts","Paul Gilbert"],
    (6,20): ["Ernest Borgnine","Arthur Godfrey","Don Rickles","John Wayne","Slappy White"],
    (6,21): ["David Birney","Meredith Baxter-Birney","Rip Taylor","Slappy White","Jo Anne Worley"],
    (6,22): ["Charlie Callas","Johnny Carson","Sandy Duncan","Arthur Godfrey"],
    (6,23): ["Dom DeLuise"],
    (6,24): ["Ernest Borgnine","Sammy Davis Jr.","Robert Goulet","Rip Taylor","Jo Anne Worley"],
}

SEASON_YEARS = {1: "1968", 2: "1968-1969", 3: "1969-1970", 4: "1970-1971", 5: "1971-1972", 6: "1972-1973"}
SEASON_EP_COUNT = {1: 14, 2: 26, 3: 26, 4: 26, 5: 24, 6: 24}

# ── Helpers ───────────────────────────────────────────────────────────────────

def safe_filename(name):
    name = re.sub(r'[^\w\-.]', '_', name.strip())
    return re.sub(r'_+', '_', name).strip('_')

def download(url, dest_path, label=''):
    if dest_path.exists() and dest_path.stat().st_size > 500:
        return True
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
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
    url = f"https://api.themoviedb.org/3{path}?api_key={TMDB_KEY}&language=en-US&append_to_response=credits"
    try:
        with urllib.request.urlopen(url, timeout=12) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  API error {path}: {e}")
        return None

def merge_guests(epguides_guests, tmdb_guests):
    """Merge guest lists, epguides is authoritative, TMDB adds extras."""
    merged = list(epguides_guests)
    for g in tmdb_guests:
        name = g.get('name', '')
        if name and name not in merged:
            merged.append(name)
    return merged

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Laugh-In TMDB Enrichment Script")
    print("=" * 50)

    IMG_DIR.mkdir(parents=True, exist_ok=True)

    report = []
    seasons_data = []

    # Fetch show-level info
    print("\nFetching show info...")
    show_info = tmdb_api(f'/tv/{SHOW_TMDB_ID}')
    time.sleep(DELAY)

    show_backdrop = ''
    show_poster = './images/laugh_in/laugh_in_poster.jpg'

    if show_info:
        if show_info.get('backdrop_path'):
            url = TMDB_BACKDROP + show_info['backdrop_path']
            dest = IMG_DIR / 'laugh_in_backdrop.jpg'
            if download(url, dest, 'show backdrop'):
                show_backdrop = './images/laugh_in/laugh_in_backdrop.jpg'
                print(f"  ✓ Show backdrop downloaded")
            time.sleep(DELAY)

        if show_info.get('poster_path'):
            url = TMDB_POSTER + show_info['poster_path']
            dest = IMG_DIR / 'laugh_in_poster.jpg'
            if download(url, dest, 'show poster'):
                print(f"  ✓ Show poster downloaded")
            time.sleep(DELAY)

    # Process each season
    for season_num in range(1, 7):
        print(f"\n── Season {season_num} ({'─'*40})")
        season_data = tmdb_api(f'/tv/{SHOW_TMDB_ID}/season/{season_num}')
        time.sleep(DELAY)

        # Download season poster if available
        season_poster = ''
        if season_data and season_data.get('poster_path'):
            url = TMDB_POSTER + season_data['poster_path']
            dest = IMG_DIR / f'season_{season_num}_poster.jpg'
            if download(url, dest, f'S{season_num} poster'):
                season_poster = f'./images/laugh_in/season_{season_num}_poster.jpg'
            time.sleep(DELAY)

        tmdb_episodes = {}
        if season_data and season_data.get('episodes'):
            for ep in season_data['episodes']:
                tmdb_episodes[ep['episode_number']] = ep
            print(f"  TMDB returned {len(tmdb_episodes)} episodes")
        else:
            print(f"  No TMDB episode data for season {season_num}")

        episodes = []
        ep_count = SEASON_EP_COUNT[season_num]

        for ep_num in range(1, ep_count + 1):
            key = (season_num, ep_num)
            epguides_guests = EPGUIDES_DATA.get(key, [])
            tmdb_ep = tmdb_episodes.get(ep_num, {})

            # Get TMDB data
            tmdb_name     = tmdb_ep.get('name', f'Episode {ep_num}')
            tmdb_overview = tmdb_ep.get('overview', '')
            tmdb_airdate  = tmdb_ep.get('air_date', '')
            tmdb_still    = tmdb_ep.get('still_path', '')
            tmdb_guests   = tmdb_ep.get('guest_stars', [])

            # Merge guests
            all_guests = merge_guests(epguides_guests, tmdb_guests)

            # Download episode still
            still_local = ''
            if tmdb_still:
                filename = f's{season_num}e{ep_num:02d}_still.jpg'
                dest = IMG_DIR / filename
                url = TMDB_STILL_LG + tmdb_still
                if download(url, dest, f'S{season_num}E{ep_num}'):
                    still_local = f'./images/laugh_in/{filename}'
                time.sleep(DELAY)

            ep_entry = {
                'num':      ep_num,
                'title':    tmdb_name,
                'airdate':  tmdb_airdate,
                'guests':   all_guests,
                'desc':     tmdb_overview,
                'still':    still_local,
            }
            episodes.append(ep_entry)

            has_still = '✓' if still_local else '✗'
            has_desc  = '✓' if tmdb_overview else '✗'
            print(f"  S{season_num}E{ep_num:02d} still={has_still} desc={has_desc} guests={len(all_guests)}")
            report.append(f"S{season_num}E{ep_num:02d} | still={'YES' if still_local else 'NO'} | desc={'YES' if tmdb_overview else 'NO'} | guests={len(all_guests)} | {', '.join(all_guests[:4])}")

        seasons_data.append({
            'num':    season_num,
            'year':   SEASON_YEARS[season_num],
            'poster': season_poster,
            'episodes': episodes
        })

    # Build complete show entry
    laugh_in = {
        "id": "laugh-in",
        "title": "Rowan & Martin's Laugh-In",
        "category": "Variety Series",
        "network": "NBC",
        "years": "1968-1973",
        "collectionNote": "",
        "tmdbId": SHOW_TMDB_ID,
        "stars": ["Dan Rowan", "Dick Martin"],
        "description": "The wildly innovative comedy-variety series that changed television forever. Rowan & Martin's Laugh-In pioneered rapid-fire sketch comedy, catchphrases, and political satire — launching the careers of Goldie Hawn and Lily Tomlin while attracting an extraordinary parade of guests from Richard Nixon to Ringo Starr.",
        "cast": [
            {"actor": "Dan Rowan", "character": "Host"},
            {"actor": "Dick Martin", "character": "Host"},
            {"actor": "Goldie Hawn", "character": "Regular"},
            {"actor": "Lily Tomlin", "character": "Regular"},
            {"actor": "Arte Johnson", "character": "Regular"},
            {"actor": "Ruth Buzzi", "character": "Regular"},
            {"actor": "Jo Anne Worley", "character": "Regular"},
            {"actor": "Henry Gibson", "character": "Regular"},
            {"actor": "Gary Owens", "character": "Regular"},
            {"actor": "Judy Carne", "character": "Regular"},
            {"actor": "Alan Sues", "character": "Regular"},
            {"actor": "Dave Madden", "character": "Regular"},
            {"actor": "Teresa Graves", "character": "Regular"},
            {"actor": "Johnny Brown", "character": "Regular"}
        ],
        "seasons": seasons_data,
        "customImage": "https://www.themoviedb.org/t/p/w600_and_h900_face/abMymAYr5R1yVeNl9NZs3x27RoY.jpg",
        "localPoster": show_poster,
        "localBackdrop": show_backdrop,
    }

    # Save laugh_in_data.json
    with open('laugh_in_data.json', 'w') as f:
        json.dump(laugh_in, f, separators=(',', ':'), ensure_ascii=False)
    print(f"\n✓ laugh_in_data.json saved")

    # Save report
    with open('laugh_in_report.txt', 'w') as f:
        f.write('\n'.join(report))
    print(f"✓ laugh_in_report.txt saved")

    # Summary
    total_eps = sum(len(s['episodes']) for s in seasons_data)
    total_stills = sum(1 for s in seasons_data for e in s['episodes'] if e.get('still'))
    total_descs = sum(1 for s in seasons_data for e in s['episodes'] if e.get('desc'))
    img_count = len(list(IMG_DIR.iterdir()))

    print(f"\n=== DONE ===")
    print(f"  Episodes:       {total_eps}")
    print(f"  With stills:    {total_stills}/{total_eps}")
    print(f"  With overview:  {total_descs}/{total_eps}")
    print(f"  Images saved:   {img_count}")
    print(f"\nNext step: upload laugh_in_data.json to Claude to build the hub.")

if __name__ == '__main__':
    main()
