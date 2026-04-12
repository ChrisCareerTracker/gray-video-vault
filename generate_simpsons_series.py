#!/usr/bin/env python3
"""
Gray Video Vault — Simpsons Series Shell Generator
Generates simpsons_series.json — the lightweight hub metadata file.
Run this AFTER all five enrichment scripts have completed.
Output: simpsons_series.json
"""

import os, json

BASE = os.path.dirname(os.path.abspath(__file__))

# Era JSON files to read episode counts from (if they exist)
ERA_FILES = [
    ('golden',   'simpsons_golden.json'),
    ('classic',  'simpsons_classic.json'),
    ('middle',   'simpsons_middle.json'),
    ('modern_a', 'simpsons_modern_a.json'),
    ('modern_b', 'simpsons_modern_b.json'),
]

def count_episodes(filename):
    path = os.path.join(BASE, filename)
    if not os.path.exists(path):
        return 0
    try:
        data = json.load(open(path, encoding='utf-8'))
        return data.get('episode_count', len(data.get('episodes', [])))
    except Exception:
        return 0

def main():
    print('Generating simpsons_series.json...')

    # Count episodes from completed files
    counts = {key: count_episodes(fname) for key, fname in ERA_FILES}
    total = sum(counts.values())

    series = {
        'tmdb_id': 456,
        'title': 'The Simpsons',
        'network': 'Fox',
        'years': '1989–present',
        'hero':    './images/simpsons/hero.jpg',
        'backdrop': './images/simpsons/backdrop.jpg',
        'description': 'The longest-running American animated series and primetime scripted TV series, following the dysfunctional Simpson family in Springfield. Created by Matt Groening.',
        'total_episodes': total,

        # Character roster for the character strip
        'characters': [
            {'id': 'homer',            'name': 'Homer Simpson',        'portrait': './images/simpsons/characters/homer.jpg'},
            {'id': 'marge',            'name': 'Marge Simpson',        'portrait': './images/simpsons/characters/marge.jpg'},
            {'id': 'bart',             'name': 'Bart Simpson',         'portrait': './images/simpsons/characters/bart.jpg'},
            {'id': 'lisa',             'name': 'Lisa Simpson',         'portrait': './images/simpsons/characters/lisa.jpg'},
            {'id': 'maggie',           'name': 'Maggie Simpson',       'portrait': './images/simpsons/characters/maggie.jpg'},
            {'id': 'burns',            'name': 'Mr. Burns',            'portrait': './images/simpsons/characters/burns.jpg'},
            {'id': 'flanders',         'name': 'Ned Flanders',         'portrait': './images/simpsons/characters/flanders.jpg'},
            {'id': 'moe',              'name': 'Moe Szyslak',          'portrait': './images/simpsons/characters/moe.jpg'},
            {'id': 'milhouse',         'name': 'Milhouse Van Houten',  'portrait': './images/simpsons/characters/milhouse.jpg'},
            {'id': 'krusty',           'name': 'Krusty the Clown',     'portrait': './images/simpsons/characters/krusty.jpg'},
            {'id': 'sideshow_bob',     'name': 'Sideshow Bob',         'portrait': './images/simpsons/characters/sideshow_bob.jpg'},
            {'id': 'apu',              'name': 'Apu Nahasapeemapetilon','portrait': './images/simpsons/characters/apu.jpg'},
            {'id': 'barney',           'name': 'Barney Gumble',        'portrait': './images/simpsons/characters/barney.jpg'},
            {'id': 'wiggum',           'name': 'Chief Wiggum',         'portrait': './images/simpsons/characters/wiggum.jpg'},
            {'id': 'skinner',          'name': 'Principal Skinner',    'portrait': './images/simpsons/characters/skinner.jpg'},
            {'id': 'smithers',         'name': 'Waylon Smithers',      'portrait': './images/simpsons/characters/smithers.jpg'},
            {'id': 'ralph',            'name': 'Ralph Wiggum',         'portrait': './images/simpsons/characters/ralph.jpg'},
            {'id': 'nelson',           'name': 'Nelson Muntz',         'portrait': './images/simpsons/characters/nelson.jpg'},
            {'id': 'lenny_carl',       'name': 'Lenny & Carl',         'portrait': './images/simpsons/characters/lenny_carl.jpg'},
            {'id': 'grandpa',          'name': 'Grampa Simpson',       'portrait': './images/simpsons/characters/grandpa.jpg'},
            {'id': 'fat_tony',         'name': 'Fat Tony',             'portrait': './images/simpsons/characters/fat_tony.jpg'},
            {'id': 'snake',            'name': 'Snake Jailbird',       'portrait': './images/simpsons/characters/snake.jpg'},
            {'id': 'comic_book_guy',   'name': 'Comic Book Guy',       'portrait': './images/simpsons/characters/comic_book_guy.jpg'},
            {'id': 'sideshow_mel',     'name': 'Sideshow Mel',         'portrait': './images/simpsons/characters/sideshow_mel.jpg'},
            {'id': 'patty_selma',      'name': 'Patty & Selma',        'portrait': './images/simpsons/characters/patty_selma.jpg'},
            {'id': 'lionel_hutz',      'name': 'Lionel Hutz',          'portrait': './images/simpsons/characters/lionel_hutz.jpg'},
            {'id': 'chalmers',         'name': 'Superintendent Chalmers','portrait': './images/simpsons/characters/chalmers.jpg'},
            {'id': 'kent_brockman',    'name': 'Kent Brockman',        'portrait': './images/simpsons/characters/kent_brockman.jpg'},
            {'id': 'dr_nick',          'name': 'Dr. Nick Riviera',     'portrait': './images/simpsons/characters/dr_nick.jpg'},
            {'id': 'professor_frink',  'name': 'Professor Frink',      'portrait': './images/simpsons/characters/professor_frink.jpg'},
            {'id': 'cletus',           'name': 'Cletus Spuckler',      'portrait': './images/simpsons/characters/cletus.jpg'},
            {'id': 'dr_hibbert',       'name': 'Dr. Hibbert',          'portrait': './images/simpsons/characters/dr_hibbert.jpg'},
            {'id': 'mayor_quimby',     'name': 'Mayor Quimby',         'portrait': './images/simpsons/characters/mayor_quimby.jpg'},
            {'id': 'rainier_wolfcastle','name': 'Rainier Wolfcastle / McBain','portrait': './images/simpsons/characters/rainier_wolfcastle.jpg'},
        ],

        # Era definitions
        'eras': [
            {
                'id':           'golden',
                'label':        'The Golden Age',
                'seasons':      '1–8',
                'years':        '1989–1997',
                'episode_count': counts['golden'],
                'description':  'The untouchable era. From Homer\'s Odyssey to You Only Move Twice.',
                'data_file':    'simpsons_golden.json',
                'available':    counts['golden'] > 0
            },
            {
                'id':           'classic',
                'label':        'The Classic Era',
                'seasons':      '9–12',
                'years':        '1997–2001',
                'episode_count': counts['classic'],
                'description':  'Still unmissable, but the cracks begin. Homer\'s Enemy. Trash of the Titans.',
                'data_file':    'simpsons_classic.json',
                'available':    counts['classic'] > 0
            },
            {
                'id':           'middle',
                'label':        'The Middle Years',
                'seasons':      '13–20',
                'years':        '2001–2009',
                'episode_count': counts['middle'],
                'description':  'The show reinvents itself. Bolder experiments, bigger guests, and the Movie.',
                'data_file':    'simpsons_middle.json',
                'available':    counts['middle'] > 0
            },
            {
                'id':           'modern_a',
                'label':        'The Modern Era',
                'seasons':      '21–28',
                'years':        '2009–2017',
                'episode_count': counts['modern_a'],
                'description':  'The long run continues. Springfield keeps evolving with the times.',
                'data_file':    'simpsons_modern_a.json',
                'available':    counts['modern_a'] > 0
            },
            {
                'id':           'modern_b',
                'label':        'The Modern Era',
                'seasons':      '29–37',
                'years':        '2017–present',
                'episode_count': counts['modern_b'],
                'description':  'Springfield in the streaming age. Collection through Season 37.',
                'data_file':    'simpsons_modern_b.json',
                'available':    counts['modern_b'] > 0
            }
        ]
    }

    out_path = os.path.join(BASE, 'simpsons_series.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(series, f, ensure_ascii=False, indent=2)

    print(f'\nDONE — simpsons_series.json written')
    print(f'Total episodes catalogued: {total}')
    print('\nEra breakdown:')
    for key, fname in ERA_FILES:
        c = counts[key]
        status = f'{c} episodes' if c > 0 else 'NOT YET GENERATED'
        print(f'  {key:12s}: {status}')

if __name__ == '__main__':
    main()
