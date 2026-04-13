#!/usr/bin/env python3
"""
Looney Tunes Character Enrichment Script
=========================================
Run from the folder containing looney_tunes_enriched_final.json

Layers (in order):
  1. TMDB /movie/{id}/credits  — character names from cast
  2. Desc/title text inference — keyword matching against known character names
  3. Series/era rules          — Bosko (1930-33), Buddy (1933-35), Foxy (1931), etc.
  4. Manual overrides          — hardcoded corrections for known edge cases

Output: looney_tunes_enriched_final.json (updated in place, backup saved)
        enrich_report.txt — full log of every change and every flagged uncertainty
"""

import json, re, time, urllib.request, urllib.error, os, shutil
from collections import defaultdict

# ── Config ────────────────────────────────────────────────────────────────────
TMDB_KEY      = '573382ec2121f69d6a89fce35293591a'
INPUT_FILE    = 'looney_tunes_enriched_final.json'
BACKUP_FILE   = 'looney_tunes_enriched_final.BACKUP.json'
REPORT_FILE   = 'enrich_report.txt'
DELAY         = 0.22   # seconds between TMDB calls — stays under rate limit

# ── TMDB character name → canonical LT name ───────────────────────────────────
# TMDB often uses variant spellings or full names
TMDB_NAME_MAP = {
    'bugs bunny':               'Bugs Bunny',
    'bugs':                     'Bugs Bunny',
    'daffy duck':               'Daffy Duck',
    'daffy':                    'Daffy Duck',
    'porky pig':                'Porky Pig',
    'porky':                    'Porky Pig',
    'elmer fudd':               'Elmer Fudd',
    'elmer':                    'Elmer Fudd',
    'tweety':                   'Tweety Bird',
    'tweety bird':              'Tweety Bird',
    'sylvester':                'Sylvester the Cat',
    'sylvester the cat':        'Sylvester the Cat',
    'sylvester j. pussycat':    'Sylvester the Cat',
    'sylvester jr':             'Sylvester Junior',
    'sylvester jr.':            'Sylvester Junior',
    "sylvester junior":         'Sylvester Junior',
    'yosemite sam':             'Yosemite Sam',
    'sam':                      'Yosemite Sam',
    'foghorn leghorn':          'Foghorn Leghorn',
    'foghorn':                  'Foghorn Leghorn',
    'road runner':              'Road Runner',
    'the road runner':          'Road Runner',
    'wile e. coyote':           'Wile E. Coyote',
    'wile e coyote':            'Wile E. Coyote',
    'wile e.':                  'Wile E. Coyote',
    'the coyote':               'Wile E. Coyote',
    'pepé le pew':              'Pepé Le Pew',
    'pepe le pew':              'Pepé Le Pew',
    'pepé':                     'Pepé Le Pew',
    'pepe':                     'Pepé Le Pew',
    'speedy gonzales':          'Speedy Gonzales',
    'speedy':                   'Speedy Gonzales',
    'marvin the martian':       'Marvin the Martian',
    'marvin':                   'Marvin the Martian',
    'tasmanian devil':          'Tasmanian Devil',
    'taz':                      'Tasmanian Devil',
    'tweety and sylvester':     'Tweety Bird',
    'granny':                   'Granny',
    'witch hazel':              'Witch Hazel',
    'henery hawk':              'Henery Hawk',
    'henery':                   'Henery Hawk',
    'gossamer':                 'Gossamer',
    'hippety hopper':           'Hippety Hopper',
    'barnyard dawg':            'Barnyard Dawg',
    'barnyard dog':             'Barnyard Dawg',
    'marc antony':              'Marc Antony',
    'marc anthony':             'Marc Antony',
    'pussyfoot':                'Pussyfoot',
    'hubie':                    'Hubie',
    'bertie':                   'Hubie',
    'hubie and bertie':         'Hubie',
    'sniffles':                 'Sniffles',
    'bosko':                    'Bosko',
    'buddy':                    'Buddy',
    'honey':                    'Honey',
    'miss prissy':              'Miss Prissy',
    'miss prissy the hen':      'Miss Prissy',
    'charlie dog':              'Charlie Dog',
    'charlie':                  'Charlie Dog',
    'ralph wolf':               'Ralph Wolf',
    'sam sheepdog':             'Sam Sheepdog',
    'michigan j. frog':         'Michigan J. Frog',
    'michigan j frog':          'Michigan J. Frog',
    'michigan':                 'Michigan J. Frog',
    'pete puma':                'Pete Puma',
    'beaky buzzard':            'Beaky Buzzard',
    'beaky':                    'Beaky Buzzard',
    'inki':                     'Inki',
    'cecil turtle':             'Cecil Turtle',
    'the minah bird':           'The Minah Bird',
    'minah bird':               'The Minah Bird',
    'rocky':                    'Rocky',
    'penelope pussycat':        'Penelope Pussycat',
    'penelope':                 'Penelope Pussycat',
    'hector the bulldog':       'Hector the Bulldog',
    'hector':                   'Hector the Bulldog',
    'claude cat':               'Claude Cat',
    'claude':                   'Claude Cat',
    'three bears':              'The Three Bears',
    'the three bears':          'The Three Bears',
    'papa bear':                'The Three Bears',
    'junior bear':              'The Three Bears',
    'ralph phillips':           'Ralph Phillips',
    'tommy cat':                'Tommy Cat',
    'tasmanian she-devil':      'Tasmanian Devil',
    'sylvester jr.':            'Sylvester Junior',
    'merlin the magic mouse':   'Merlin the Magic Mouse',
}

# ── Desc/title keyword rules ───────────────────────────────────────────────────
# Each entry: (regex_pattern, [characters_to_add])
# Applied to (title + ' ' + desc + ' ' + commentary).lower()
DESC_RULES = [
    # Bugs Bunny
    (r'\bbugs bunny\b|\bbugs\b(?! eye| fix| me| out| off| up| in| into| him| her| the| a | on | about| with)',
     ['Bugs Bunny']),
    # Daffy Duck
    (r'\bdaffy duck\b|\bdaffy\b',          ['Daffy Duck']),
    # Porky Pig
    (r'\bporky pig\b|\bporky\b',           ['Porky Pig']),
    # Elmer Fudd
    (r'\belmer fudd\b|\belmer\b',          ['Elmer Fudd']),
    # Tweety
    (r'\btweety\b',                         ['Tweety Bird']),
    # Sylvester
    (r'\bsylvester\b(?! jr)',              ['Sylvester the Cat']),
    # Sylvester Jr
    (r'\bsylvester jr\b',                  ['Sylvester Junior']),
    # Yosemite Sam
    (r'\byosemite sam\b|\byosemite\b',     ['Yosemite Sam']),
    # Foghorn Leghorn
    (r'\bfoghorn leghorn\b|\bfoghorn\b',   ['Foghorn Leghorn']),
    # Road Runner
    (r'\broad.runner\b',                   ['Road Runner']),
    # Wile E. Coyote
    (r'\bwile e\.?\b|\bcoyote\b(?! ugly)',  ['Wile E. Coyote']),
    # Pepé Le Pew
    (r'\bpep[eé]\b|\bpep[eé] le pew\b|\bskunk\b(?!s)',  ['Pepé Le Pew']),
    # Speedy Gonzales
    (r'\bspeedy gonzales\b|\bspeedy\b',    ['Speedy Gonzales']),
    # Marvin the Martian
    (r'\bmarvin the martian\b|\bmarvin\b(?! gardens)',  ['Marvin the Martian']),
    # Tasmanian Devil
    (r'\btasmanian devil\b|\btaz\b',       ['Tasmanian Devil']),
    # Granny
    (r'\bgranny\b',                        ['Granny']),
    # Witch Hazel
    (r'\bwitch hazel\b',                   ['Witch Hazel']),
    # Henery Hawk
    (r'\bhenery hawk\b|\bhenery\b|\bhenry hawk\b', ['Henery Hawk']),
    # Gossamer
    (r'\bgossamer\b|\bhairy monster\b|\bred monster\b', ['Gossamer']),
    # Hippety Hopper
    (r'\bhippety hopper\b|\bhippety\b',    ['Hippety Hopper']),
    # Barnyard Dawg
    (r'\bbarnyard dawg\b|\bbarnyard dog\b', ['Barnyard Dawg']),
    # Marc Antony & Pussyfoot
    (r'\bmarc ant[ho]n[iy]\b',             ['Marc Antony', 'Pussyfoot']),
    (r'\bpussyfoot\b',                     ['Marc Antony', 'Pussyfoot']),
    # Hubie and Bertie
    (r'\bhubie\b|\bbertie\b|\bhubie and bertie\b', ['Hubie']),
    # Sniffles
    (r'\bsniffles\b',                      ['Sniffles']),
    # Bosko
    (r'\bbosko\b',                         ['Bosko']),
    # Buddy
    (r'\bbuddy\b(?! holly| rich| system|\'s)',  ['Buddy']),
    # Honey (early Harman)
    (r'\bhoney\b(?! bee| badger| pot| moon| dew)',  ['Honey']),
    # Miss Prissy
    (r'\bmiss prissy\b|\bspinster hen\b',  ['Miss Prissy']),
    # Charlie Dog
    (r'\bcharlie dog\b',                   ['Charlie Dog']),
    # Ralph Wolf & Sam Sheepdog
    (r'\bralph wolf\b',                    ['Ralph Wolf', 'Sam Sheepdog']),
    (r'\bsam sheepdog\b|\bsheepdog\b',     ['Ralph Wolf', 'Sam Sheepdog']),
    # Michigan J. Frog
    (r'\bmichigan j\.? frog\b|\bmichigan\b(?! ave| state| city)', ['Michigan J. Frog']),
    # Pete Puma
    (r'\bpete puma\b',                     ['Pete Puma']),
    # Beaky Buzzard
    (r'\bbeaky buzzard\b|\bbeaky\b',       ['Beaky Buzzard']),
    # Inki
    (r'\binki\b',                          ['Inki']),
    # Cecil Turtle
    (r'\bcecil turtle\b|\bcecil\b',        ['Cecil Turtle']),
    # The Minah Bird
    (r'\bminah bird\b|\bmyna bird\b',      ['The Minah Bird']),
    # Rocky
    (r'\brocky\b(?! balboa| mountains)',   ['Rocky']),
    # Penelope Pussycat
    (r'\bpenelope\b',                      ['Penelope Pussycat', 'Pepé Le Pew']),
    # Hector the Bulldog
    (r'\bhector\b(?! the great| berlioz)',  ['Hector the Bulldog']),
    # Claude Cat
    (r'\bclaude cat\b',                    ['Claude Cat']),
    # Three Bears
    (r'\bthree bears\b|\bpapa bear\b|\bjunior bear\b|\bjunyer bear\b', ['The Three Bears']),
    # Ralph Phillips
    (r'\bralph phillips\b',                ['Ralph Phillips']),
    # Tommy Cat
    (r'\btommy cat\b',                     ['Tommy Cat']),
    # Sylvester Jr
    (r'\bsylvester jr\.?\b|\bjunior\b(?= bear| learns| cries| sob)',  ['Sylvester Junior']),
    # Merlin
    (r'\bmerlin the magic mouse\b|\bmerlin\b(?= the magic)',  ['Merlin the Magic Mouse']),
]

# ── Era/series rules (applied when desc inference yields nothing) ─────────────
# Format: (year_start, year_end, director_patterns, title_patterns, characters)
ERA_RULES = [
    # Foxy — early Merrie Melodies 1931 (Ising)
    (1930, 1931, ['Rudolf Ising'], [r'foxy|lady.*mandolin|one more time|smile.*darn|don.*know.*doin'], ['Foxy']),
    # Bosko era — Harman/Ising 1930-1933
    (1930, 1933, ['Hugh Harman', 'Rudolf Ising', 'Friz Freleng'], [], ['Bosko']),
    # Buddy era — 1933-1935 (various directors)
    (1933, 1935, ['Earl Duvall', 'Tom Palmer', 'Jack King', 'Ben Hardaway', 'Friz Freleng',
                  'Cal Dalton', 'Ub Iwerks'], [], ['Buddy']),
    # Merrie Melodies one-shots 1931-1933 — no recurring chars
    # (leave empty — these are the "spot-gag" films)
]

# ── Hard overrides — specific cartoon titles → definitive character list ──────
# Use when automated methods would get it wrong
HARD_OVERRIDES = {
    # Foxy cartoons
    "Lady, Play Your Mandolin!":   ['Foxy'],
    "One More Time":               ['Foxy'],
    "Smile, Darn Ya, Smile!":      ['Foxy'],
    "You Don't Know What You're Doin'!": ['Piggy'],
    "Goopy Geer":                  ['Goopy Geer'],
    # Spot-gag / one-shot MM 1930s — genuinely no recurring characters
    "A Great Big Bunch of You":    [],
    "I Love A Parade":             [],
    "I Wish I Had Wings":          [],
    "Moonlight for Two":           [],
    "You're Too Careless With Your Kisses!": ['Honey'],
    "Shuffle Off to Buffalo":      [],
    "Young and Healthy":           [],
    "Shake Your Powder Puff":      [],
    "The Girl at the Ironing Board": [],
    "The Miller's Daughter":       [],
    "Those Were Wonderful Days":   [],
    "Why Do I Dream Those Dreams": [],
    "Beauty and the Beast":        [],
    "Country Boy":                 [],
    "Mr. and Mrs. Is the Name":    [],
    "My Green Fedora":             [],
    "The Fire Alarm":              [],
    "Into Your Dance":             [],
    "rhythm in the bow":           [],
    "Let It Be Me":                ['Bingo', 'Emily'],
    "The CooCoo Nut Grove":        [],
    "Page Miss Glory":             [],
    "Pigs Is Pigs":                [],
    "The Phantom Ship":            ['Beans the Cat'],
    # 1940s spot-gags
    "A Gander at Mother Goose":    [],
    "Busy Bakers":                 [],
    "Ceiling Hero":                [],
    "Circus Today":                [],
    "Cross Country Detours":       [],
    "Gallopin' Gals":              [],
    "Shop, Look and Listen":       [],
    "Sportsman Woo":               [],
    "The Crackpot Quail":          [],
    "The Hardship of Miles Standish": [],
    "The Haunted Mouse":           [],
    "Tortoise Beats Hare":         ['Bugs Bunny', 'Cecil Turtle'],
    "The Early Worm Gets the Bird":['Beaky Buzzard'],
    # 1950s
    "A Bone for a Bone":           ['Gopher'],
    "Corn Plastered":              [],
    "Crows Feat":                  [],
    "Nelly's Folly":               ['Nelly'],
    "Martian Through Georgia":     ['Marvin the Martian'],
    "Now Hear This":               [],
    "Bartholomew versus the Wheel":[],
    "Norman Normal":               [],
    "Señorella and the Glass Huarache": ['Speedy Gonzales'],
    # Elmer + early Bugs
    "Elmer's Candid Camera":       ['Elmer Fudd', 'Bugs Bunny'],
    "Ghost Wanted":                [],
    # Charlie Dog
    "A Hound For Trouble":         ['Charlie Dog'],
    "Little Goes a Long Way":      ['Charlie Dog'],
    # Chow Hound
    "Chow Hound":                  ['Granny'],
    # Foxy By Proxy
    "Foxy By Proxy:":              ['Bugs Bunny'],
    "Foxy By Proxy":               ['Bugs Bunny'],
    # Sleepy Time Possum
    "Sleepy Time Possum":          [],
    # Early to Bet
    "Early to Bet":                [],
    # Transylvania
    "Transylvania 6-5000":         ['Bugs Bunny'],
    # False positive fixes — these cartoons have character-like words in desc
    # but don't actually feature those LT characters
    "Country Mouse":               [],          # Elmer = mouse character name, not Elmer Fudd
    "My Green Fedora":             [],          # Elmer = baby rabbit, not Elmer Fudd
    "The Lady in Red":             [],          # No Bugs Bunny — cockroach café cartoon
    "Bingo Crosbyana":             [],          # No Bugs — Bing Crosby parody insects
    "Streamlined Greta Green":     [],          # No Speedy — anthropomorphic cars
    "Wacky Wildlife":              [],          # No Wile E. — spot-gag nature cartoon
    "Cross Country Detours":       [],          # No Yosemite Sam — spot-gag travelogue
    "Moonlight for Two":           [],          # No Honey (LT char) — square dance cartoon
    "Mr. and Mrs. Is the Name":    ['Buddy'],   # Buddy and Cookie, not general "Buddy"
    "I Wanna Play House":          ['The Three Bears'],  # Bear cubs = Three Bears universe
    "The Bears Tale":              ['The Three Bears'],  # Goldilocks retelling
    "Little Red Walking Hood":     ['Elmer Fudd'],  # Confirmed early Elmer appearance
    "I Haven't Got a Hat":         ['Porky Pig'],   # Porky's debut — confirmed
    "Wholly Smoke":                ['Porky Pig'],
    "Chicken Jitters":             ['Porky Pig'],
    "Prest-O Change-O":            ['Bugs Bunny'],  # early proto-Bugs
    "Cinderella Meets Fella":      ['Elmer Fudd'],
    "A Day at the Zoo":            ['Elmer Fudd'],
    "Slap Happy Pappy":            ['Porky Pig'],
    "Rover's Rival":               ['Porky Pig'],
    "The Village Smithy":          ['Porky Pig'],
    "Alpine Antics":               ['Porky Pig'],
    "The Chewin Bruin":            ['Porky Pig'],
    "Elmer's Candid Camera":       ['Elmer Fudd', 'Bugs Bunny'],
    "It's an Ill Wind":            ['Porky Pig'],
    "Poultry Pirates":             ['Porky Pig'],
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def normalize_char_name(raw):
    """Map raw TMDB character name to canonical LT name, or None to skip."""
    key = raw.strip().lower()
    # Direct match
    if key in TMDB_NAME_MAP:
        return TMDB_NAME_MAP[key]
    # Partial match — if any known key is contained in the raw name
    for k, v in TMDB_NAME_MAP.items():
        if k in key:
            return v
    # Skip voice actor names, "Self", "Narrator", generic roles
    skip_patterns = ['narrator', 'self', 'voice', 'various', 'himself',
                     'additional', 'extra', 'uncredited', 'announcer']
    if any(p in key for p in skip_patterns):
        return None
    return None  # Unknown — don't add

def fetch_tmdb_credits(tmdb_id):
    """Return (characters[], voice_cast[]) from TMDB, or (None, None) on error."""
    url = (f"https://api.themoviedb.org/3/movie/{tmdb_id}/credits"
           f"?api_key={TMDB_KEY}&language=en-US")
    try:
        with urllib.request.urlopen(url, timeout=12) as r:
            data = json.loads(r.read())
        chars, cast_names = [], []
        for actor in data.get('cast', []):
            char_raw  = actor.get('character', '')
            actor_name = actor.get('name', '')
            if actor_name:
                cast_names.append(actor_name)
            canonical = normalize_char_name(char_raw)
            if canonical and canonical not in chars:
                chars.append(canonical)
        return chars, cast_names
    except urllib.error.HTTPError as e:
        return None, None
    except Exception:
        return None, None

def infer_from_desc(cartoon):
    """Return list of character names inferred from title+desc+commentary text."""
    def s(v): return v if isinstance(v, str) else ''
    text = ' '.join([
        s(cartoon.get('title')),
        s(cartoon.get('desc')),
        s(cartoon.get('tmdb_overview')),
        s(cartoon.get('commentary')),
        s(cartoon.get('tags')),
    ]).lower()

    found = set()
    for pattern, chars in DESC_RULES:
        if re.search(pattern, text):
            for ch in chars:
                found.add(ch)
    return sorted(found)

def apply_era_rules(cartoon):
    """Return characters from era/series rules, or [] if none match."""
    year     = cartoon.get('year', 0)
    director = cartoon.get('director', '')
    title    = cartoon.get('title', '').lower()

    for y_start, y_end, directors, title_patterns, chars in ERA_RULES:
        if not (y_start <= year <= y_end):
            continue
        dir_match = any(d in director for d in directors) if directors else True
        title_match = True
        if title_patterns:
            title_match = any(re.search(p, title) for p in title_patterns)
        if dir_match and title_match:
            return chars
    return []

def merge_chars(existing, new_chars):
    """Merge new chars into existing list, preserving order, no duplicates."""
    result = list(existing)
    for c in new_chars:
        if c not in result:
            result.append(c)
    return result

# ── Main enrichment loop ──────────────────────────────────────────────────────

def main():
    print(f"Loading {INPUT_FILE}...")
    with open(INPUT_FILE) as f:
        data = json.load(f)

    # Backup
    shutil.copy(INPUT_FILE, BACKUP_FILE)
    print(f"Backup saved to {BACKUP_FILE}")

    # Flatten for processing
    all_cartoons = []
    for decade_key, decade_data in data['by_decade'].items():
        cartoons = decade_data if isinstance(decade_data, list) else decade_data.get('cartoons', [])
        for c in cartoons:
            c['_decade_key'] = decade_key
            all_cartoons.append(c)

    total          = len(all_cartoons)
    needs_chars    = [c for c in all_cartoons if not c.get('characters')]
    has_chars      = [c for c in all_cartoons if c.get('characters')]

    print(f"\nTotal cartoons: {total}")
    print(f"Already have characters: {len(has_chars)}")
    print(f"Need enrichment: {len(needs_chars)}")
    print(f"\nStarting TMDB + inference pass...\n")

    report_lines = []
    stats = defaultdict(int)

    for idx, cartoon in enumerate(all_cartoons):
        title    = cartoon.get('title', '?')
        year     = cartoon.get('year', '?')
        tmdb_id  = cartoon.get('tmdb_id')
        existing = list(cartoon.get('characters') or [])
        existing_cast = list(cartoon.get('voice_cast') or [])

        # ── Check hard overrides first ────────────────────────────────────────
        if title in HARD_OVERRIDES:
            override = HARD_OVERRIDES[title]
            if override != existing:
                cartoon['characters'] = override
                report_lines.append(f"[OVERRIDE] {title} ({year}): {override}")
                stats['overrides'] += 1
            continue

        # ── Skip if already fully enriched ───────────────────────────────────
        if existing:
            # Still run TMDB to potentially add voice cast
            pass

        # ── Layer 1: TMDB credits ─────────────────────────────────────────────
        tmdb_chars, tmdb_cast = [], []
        if tmdb_id:
            tmdb_chars, tmdb_cast = fetch_tmdb_credits(tmdb_id)
            time.sleep(DELAY)
            if tmdb_chars is None:
                tmdb_chars = []
                stats['tmdb_errors'] += 1
            else:
                stats['tmdb_calls'] += 1

        # ── Layer 2: Desc inference ───────────────────────────────────────────
        desc_chars = infer_from_desc(cartoon)

        # ── Layer 3: Era rules (only if both above return nothing) ────────────
        era_chars = []
        if not tmdb_chars and not desc_chars and not existing:
            era_chars = apply_era_rules(cartoon)

        # ── Merge all sources ─────────────────────────────────────────────────
        merged_chars = merge_chars(existing, tmdb_chars)
        merged_chars = merge_chars(merged_chars, desc_chars)
        merged_chars = merge_chars(merged_chars, era_chars)

        # Merge voice cast (TMDB cast names)
        merged_cast = merge_chars(existing_cast, tmdb_cast or [])

        # ── Write back ────────────────────────────────────────────────────────
        changed_chars = merged_chars != existing
        changed_cast  = merged_cast  != existing_cast

        if changed_chars:
            cartoon['characters'] = merged_chars
            added = [c for c in merged_chars if c not in existing]
            source = []
            if any(c in tmdb_chars for c in added):    source.append('TMDB')
            if any(c in desc_chars for c in added):    source.append('DESC')
            if any(c in era_chars  for c in added):    source.append('ERA')
            report_lines.append(
                f"[CHARS] {title} ({year}) +{added} via {'+'.join(source) or 'UNKNOWN'}"
            )
            stats['chars_updated'] += 1

        if changed_cast and merged_cast:
            cartoon['voice_cast'] = merged_cast[:10]  # cap at 10
            stats['cast_updated'] += 1

        # Progress
        if (idx + 1) % 50 == 0:
            print(f"  {idx+1}/{total} processed... "
                  f"(TMDB calls: {stats['tmdb_calls']}, "
                  f"chars updated: {stats['chars_updated']})")

    # ── Final pass: flag remaining empties ───────────────────────────────────
    still_empty = [c for c in all_cartoons if not c.get('characters')]
    report_lines.append(f"\n=== STILL EMPTY AFTER ENRICHMENT ({len(still_empty)}) ===")
    for c in still_empty:
        report_lines.append(
            f"  {c['title']} ({c.get('year')}) dir={c.get('director','')} "
            f"desc={c.get('desc','')[:80]}"
        )

    # ── Save output ───────────────────────────────────────────────────────────
    print(f"\nSaving {INPUT_FILE}...")
    with open(INPUT_FILE, 'w') as f:
        json.dump(data, f, separators=(',', ':'), ensure_ascii=False)

    # ── Write report ──────────────────────────────────────────────────────────
    with open(REPORT_FILE, 'w') as f:
        f.write('\n'.join(report_lines))

    print(f"\n=== DONE ===")
    print(f"  TMDB API calls:   {stats['tmdb_calls']}")
    print(f"  TMDB errors:      {stats['tmdb_errors']}")
    print(f"  Characters updated: {stats['chars_updated']}")
    print(f"  Voice cast updated: {stats['cast_updated']}")
    print(f"  Hard overrides:   {stats['overrides']}")
    print(f"  Still empty:      {len(still_empty)}")
    print(f"\nFull report: {REPORT_FILE}")
    print(f"Backup:      {BACKUP_FILE}")

if __name__ == '__main__':
    main()
