#!/usr/bin/env python3
"""
Gray Video Vault — Troy McClure Fixes
1. Adds troy_mcclure to simpsons_series.json character list
2. Strips the bad Troy quote from Springfield Notes in all era JSONs

Zero API calls. Run from the TV Vault folder.
Usage: python3 fix_troy_series.py
"""

import os, json, re

BASE = os.path.dirname(os.path.abspath(__file__))

ERA_FILES = [
    'simpsons_golden.json',
    'simpsons_classic.json',
    'simpsons_middle.json',
    'simpsons_modern_a.json',
    'simpsons_modern_b.json',
]

def fix_series_json():
    path = os.path.join(BASE, 'simpsons_series.json')
    if not os.path.exists(path):
        print('  simpsons_series.json not found — skipping')
        return

    with open(path, encoding='utf-8') as f:
        data = json.load(f)

    chars = data.get('characters', [])
    ids = [c['id'] for c in chars]

    if 'troy_mcclure' in ids:
        print('  troy_mcclure already in simpsons_series.json')
        return

    troy_entry = {
        'id':      'troy_mcclure',
        'name':    'Troy McClure',
        'portrait': './images/simpsons/characters/troy_mcclure.jpg'
    }

    # Insert after lionel_hutz
    try:
        idx = ids.index('lionel_hutz')
        chars.insert(idx + 1, troy_entry)
        print(f'  Inserted troy_mcclure after lionel_hutz (position {idx+1})')
    except ValueError:
        chars.append(troy_entry)
        print('  Appended troy_mcclure to end of character list')

    data['characters'] = chars
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'  ✓ simpsons_series.json updated ({len(chars)} characters total)')

def strip_bad_notes():
    """
    Remove any appended Troy McClure quote from Springfield Notes.
    The bad text was appended as a sentence starting with variations of:
    'Hi, I'm Troy McClure...' or 'Troy McClure intro:...'
    Also handles cases where it was joined with '. ' to the existing note.
    """
    total_fixed = 0

    # The exact bad string that was wrongly appended
    BAD_PATTERNS = [
        # Matches '. Hi, I\'m Troy McClure...' through end of string
        r'\.\s*Hi,\s*I\'?m Troy McClure[^"]*"[^"]*"\.',
        r'\.\s*Hi,\s*I\'?m Troy McClure[^"]*"[^"]*"$',
        r'\.\s*Hi,\s*I\'?m Troy McClure.*?(?=\s*Troy McClure appears|\s*$)',
        r'\s*Hi,\s*I\'?m Troy McClure.*?(?=\s*Troy McClure appears|\s*$)',
        r'Troy McClure intro:.*?(?=\s*Troy McClure appears|\s*$)',
    ]

    for era_file in ERA_FILES:
        path = os.path.join(BASE, era_file)
        if not os.path.exists(path):
            continue

        with open(path, encoding='utf-8') as f:
            data = json.load(f)

        episodes = data.get('episodes', [])
        era_label = data.get('era_label', era_file)
        file_changed = False
        era_fixed = 0

        for ep in episodes:
            note = ep.get('notes') or ''
            if not note:
                continue

            # Check if note contains a bad Troy intro
            has_bad = any([
                "Hi, I'm Troy McClure" in note,
                "Hi, I\\'m Troy McClure" in note,
                'Troy McClure intro:' in note.lower(),
            ])

            if not has_bad:
                continue

            code = f"S{ep['season']:02d}E{ep['episode']:02d}"
            original = note

            # Find where the bad text starts
            # Look for the pattern: existing note + '. Hi, I'm Troy McClure...'
            # or '. Troy McClure intro:...'
            bad_starts = []
            for marker in ["Hi, I'm Troy McClure", "Hi, I\\'m Troy McClure", "Troy McClure intro:"]:
                idx = note.find(marker)
                if idx >= 0:
                    bad_starts.append(idx)

            if bad_starts:
                cut_at = min(bad_starts)
                # Also trim the '. ' or ' ' before the bad text
                while cut_at > 0 and note[cut_at-1] in ('. ', ' ', '.'):
                    cut_at -= 1
                    if note[cut_at] == '.':
                        # Don't eat the period if it belongs to prior sentence
                        cut_at += 1
                        break

                cleaned = note[:cut_at].rstrip('. ').strip()

                # Special case: if this is Saturdays of Thunder, preserve 
                # the Juice Loosener reference if it comes AFTER the bad text
                juice_marker = "Troy McClure appears in an infomercial for the Juice Loosener"
                if juice_marker in note and 'saturdays of thunder' in ep.get('title','').lower():
                    ep['notes'] = cleaned + '. ' + juice_marker if cleaned else juice_marker
                else:
                    ep['notes'] = cleaned if cleaned else None

                file_changed = True
                era_fixed += 1
                total_fixed += 1
                print(f'  {code} {ep["title"][:40]:<40} | fixed note')

        if file_changed:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f'  ✓ {era_file} saved ({era_fixed} notes fixed)')
        else:
            print(f'  {era_label}: no bad notes found')

    return total_fixed

def main():
    print('='*60)
    print('TROY McCLURE FIX SCRIPT')
    print('='*60)

    print('\n── Step 1: Update simpsons_series.json ──')
    fix_series_json()

    print('\n── Step 2: Strip bad Troy quotes from Springfield Notes ──')
    total = strip_bad_notes()

    print(f'\n{"="*60}')
    print('DONE')
    print(f'  Notes fixed: {total}')
    print('\nTroy McClure will now appear in the character strip.')
    print('Hard refresh your browser after moving the folder back.')
    print('='*60)

if __name__ == '__main__':
    main()
