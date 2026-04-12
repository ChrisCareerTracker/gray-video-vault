#!/usr/bin/env python3
"""
Gray Video Vault — Troy McClure & Lionel Hutz Final Patch
Hard-coded corrections — zero API calls.
Uses title matching so episode numbers don't need to be exact.
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

# ── Verified Troy McClure speaking appearances (by title) ─────
TROY_TITLES = {
    "homer vs. lisa and the 8th commandment",
    "bart's dog gets an 'f'",
    "bart's dog gets an f",
    "mr. lisa goes to washington",
    "bart the murderer",
    "treehouse of horror ii",
    "saturdays of thunder",
    "radio bart",
    "lisa the greek",
    "homer alone",
    "bart's friend falls in love",
    "a streetcar named marge",
    "itchy & scratchy: the movie",
    "marge gets a job",
    "mr. plow",
    "selma's choice",
    "duffless",
    "marge in chains",
    "krusty gets kancelled",
    "rosebud",
    "marge on the lam",
    "bart's inner child",
    "$pringfield (or, how i learned to stop worrying and love legalized gambling)",
    "$pringfield (or, how i learned to stop worrying and love legalized gambling)",
    "lady bouvier's lover",
    "grampa vs. sexual inadequacy",
    "lisa's wedding",
    "radioactive man",
    "lisa the vegetarian",
    "the simpsons 138th episode spectacular",
    "marge be not proud",
    "bart the fink",
    "lisa the iconoclast",
    "a fish called selma",
    "bart after dark",
    "hurricane neddy",
    "the itchy & scratchy & poochie show",
    "the simpsons spin-off showcase",
    "the joy of sect",
    "das bus",
    "lisa the simpson",
    "this little wiggy",
    "the trouble with trillions",
    "bart the mother",
    "another simpsons clip show",
    "bart vs. australia",
    "burns' heir",
    "the boy who knew too much",
    "secrets of a successful marriage",
}

# ── Episodes where lionel_hutz should be ADDED (by title) ─────
HUTZ_ADD_TITLES = {
    "flaming moe's",
    "new kid on the block",
}

# ── Episodes where troy_mcclure should NOT be (wrongly tagged) ─
TROY_REMOVE_TITLES = {
    "flaming moe's",        # Lionel Hutz, not Troy
    "new kid on the block", # Lionel Hutz, not Troy
}

# ── Juice Loosener note ────────────────────────────────────────
JUICE_LOOSENER = "Troy McClure appears in an infomercial for the Juice Loosener, one of his most memorably absurd product endorsements."

def norm(t):
    return t.lower().strip()

def strip_bad_troy_intro(note):
    if not note:
        return note
    cleaned = re.sub(r'\.?\s*Hi,\s*I\'?m Troy McClure[^"]*"[^"]*"\.?', '', note, flags=re.IGNORECASE)
    cleaned = re.sub(r'\.?\s*"Hi,\s*I\'?m Troy McClure.*$', '', cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r'\.?\s*Troy McClure intro:.*$', '', cleaned, flags=re.IGNORECASE | re.DOTALL)
    return cleaned.strip()

def main():
    print('='*60)
    print('TROY McCLURE & LIONEL HUTZ FINAL PATCH')
    print('Zero API calls — title-matched corrections')
    print('='*60)

    total_changed = 0

    for era_file in ERA_FILES:
        path = os.path.join(BASE, era_file)
        if not os.path.exists(path):
            print(f'\nSkipping {era_file} — not found')
            continue

        with open(path, encoding='utf-8') as f:
            data = json.load(f)

        episodes  = data.get('episodes', [])
        era_label = data.get('era_label', era_file)
        print(f'\n── {era_label} ──')

        file_changed = False

        for ep in episodes:
            s = ep['season']
            e = ep['episode']
            title_norm = norm(ep.get('title', ''))
            code = f"S{s:02d}E{e:02d}"
            chars = list(ep.get('characters', []))
            notes = ep.get('notes') or ''
            changed = False
            changes = []

            # Strip bad Troy intros from notes
            clean_notes = strip_bad_troy_intro(notes)
            if clean_notes != notes:
                ep['notes'] = clean_notes
                notes = clean_notes
                changes.append('stripped bad Troy intro')
                changed = True

            # Add Juice Loosener note to Saturdays of Thunder
            if 'saturdays of thunder' in title_norm:
                if 'juice loosener' not in notes.lower():
                    sep = '. ' if notes.strip() else ''
                    ep['notes'] = (notes.rstrip('. ') + sep + JUICE_LOOSENER).strip()
                    changes.append('added Juice Loosener note')
                    changed = True

            # Remove troy_mcclure from wrongly tagged episodes
            if title_norm in TROY_REMOVE_TITLES and 'troy_mcclure' in chars:
                chars.remove('troy_mcclure')
                changes.append('removed troy_mcclure (wrong)')
                changed = True

            # Remove troy_mcclure from ANY episode not in verified list
            if title_norm not in TROY_TITLES and 'troy_mcclure' in chars:
                chars.remove('troy_mcclure')
                changes.append('removed erroneous troy_mcclure')
                changed = True

            # Add troy_mcclure to verified episodes
            if title_norm in TROY_TITLES and 'troy_mcclure' not in chars:
                chars.append('troy_mcclure')
                changes.append('added troy_mcclure')
                changed = True

            # Add lionel_hutz where confirmed missing
            if title_norm in HUTZ_ADD_TITLES and 'lionel_hutz' not in chars:
                chars.append('lionel_hutz')
                changes.append('added lionel_hutz')
                changed = True

            if changed:
                ep['characters'] = chars
                file_changed = True
                total_changed += 1
                print(f'  {code} {ep["title"][:38]:<38} | {" · ".join(changes)}')

        if file_changed:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f'  ✓ {era_file} saved')
        else:
            print(f'  (no changes needed)')

    print(f'\n{"="*60}')
    print(f'DONE — {total_changed} episodes updated')
    print('Troy McClure and Lionel Hutz correctly tagged.')
    print('='*60)

if __name__ == '__main__':
    main()
