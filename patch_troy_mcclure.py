#!/usr/bin/env python3
"""
Gray Video Vault — Troy McClure Patch Script
Does three things in one run:
1. Adds troy_mcclure to the character list in simpsons_series.json
2. Disambiguates lionel_hutz vs troy_mcclure in all episode JSON files
3. Captures "Hi, I'm Troy McClure, you may remember me from..." intros
   and appends them to existing Springfield Notes

Run from the TV Vault folder.
Usage: python3 patch_troy_mcclure.py
"""

import os, json, time, re, requests

BASE          = os.path.dirname(os.path.abspath(__file__))
ANTHROPIC_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

ERA_FILES = [
    'simpsons_golden.json',
    'simpsons_classic.json',
    'simpsons_middle.json',
    'simpsons_modern_a.json',
    'simpsons_modern_b.json',
]

VALID_IDS = {
    'homer','marge','bart','lisa','maggie','burns','flanders','moe',
    'milhouse','krusty','sideshow_bob','apu','barney','wiggum','skinner',
    'smithers','ralph','nelson','lenny_carl','grandpa','fat_tony','snake',
    'comic_book_guy','sideshow_mel','patty_selma','lionel_hutz','chalmers',
    'kent_brockman','dr_nick','professor_frink','cletus','dr_hibbert',
    'mayor_quimby','rainier_wolfcastle','troy_mcclure'
}

def anthropic_call(prompt, max_tokens=300):
    if not ANTHROPIC_KEY:
        return None
    headers = {
        'x-api-key': ANTHROPIC_KEY,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json'
    }
    body = {
        'model': 'claude-sonnet-4-20250514',
        'max_tokens': max_tokens,
        'messages': [{'role': 'user', 'content': prompt}]
    }
    for attempt in range(3):
        try:
            r = requests.post('https://api.anthropic.com/v1/messages',
                              headers=headers, json=body, timeout=30)
            if r.status_code == 401:
                print('\n  ERROR: Anthropic key invalid (401)')
                return None
            if r.status_code == 429:
                print('  Rate limit — waiting 15s...')
                time.sleep(15)
                continue
            r.raise_for_status()
            return r.json()['content'][0]['text'].strip()
        except Exception as e:
            if attempt == 2:
                print(f'\n  API error: {e}')
                return None
            time.sleep(5)
    return None

def disambiguate_hartman(ep):
    """
    For episodes tagged with lionel_hutz, determine if it's actually Hutz,
    Troy McClure, or both. Returns dict with corrected character list.
    """
    guests_str = ', '.join([
        f"{g.get('actor','')} as {g.get('character','')}"
        for g in (ep.get('guests') or [])[:15] if g.get('actor')
    ])
    notes_str = ep.get('notes', '') or ''

    prompt = f"""You are a Simpsons expert. This episode may feature Phil Hartman characters.

Episode: S{ep['season']:02d}E{ep['episode']:02d} — "{ep['title']}"
Description: {ep.get('description', '')}
Springfield Note: {notes_str}
Guest cast: {guests_str}

Phil Hartman voiced TWO distinct recurring characters:
- LIONEL HUTZ: incompetent personal injury lawyer, always involved in lawsuits/legal cases
- TROY McCLURE: washed-up actor/host who introduces himself "Hi, I'm Troy McClure, you may remember me from..."

These are completely different characters. Determine which appear in this episode.

Return ONLY a JSON object, nothing else:
{{
  "has_lionel_hutz": true or false,
  "has_troy_mcclure": true or false,
  "troy_intro": "The exact or reconstructed 'Hi, I'm Troy McClure, you may remember me from X and Y' line if Troy appears, otherwise null"
}}

Be precise. If you are not confident Troy or Hutz appears, return false for that character."""

    text = anthropic_call(prompt, max_tokens=250)
    if not text:
        return None
    try:
        text = re.sub(r'^```[a-z]*\n?', '', text)
        text = re.sub(r'\n?```$', '', text)
        return json.loads(text)
    except:
        return None

def process_episode(ep):
    """
    Process one episode:
    - Fix lionel_hutz/troy_mcclure tagging
    - Append Troy's intro to Springfield Notes if applicable
    Returns True if anything changed.
    """
    chars = list(ep.get('characters', []))
    has_hutz  = 'lionel_hutz'   in chars
    has_troy  = 'troy_mcclure'  in chars

    # Only process if episode has Phil Hartman connection
    # Check guests for Phil Hartman OR already tagged with hutz/troy
    guest_names = [g.get('actor','') for g in (ep.get('guests') or [])]
    has_hartman_guest = 'Phil Hartman' in guest_names
    needs_check = has_hutz or has_troy or has_hartman_guest

    if not needs_check:
        return False

    code = f"S{ep['season']:02d}E{ep['episode']:02d}"
    print(f'  {code} {ep["title"][:42]:<42}', end=' ', flush=True)

    result = disambiguate_hartman(ep)
    if result is None:
        print('! (API error)')
        return False

    changed = False

    # Fix character tags
    new_chars = [c for c in chars if c not in ('lionel_hutz','troy_mcclure')]

    if result.get('has_lionel_hutz'):
        if 'lionel_hutz' not in new_chars:
            new_chars.append('lionel_hutz')
    if result.get('has_troy_mcclure'):
        if 'troy_mcclure' not in new_chars:
            new_chars.append('troy_mcclure')

    # Check if chars changed
    if set(new_chars) != set(chars):
        ep['characters'] = new_chars
        changed = True

    # Append Troy's intro to Springfield Notes
    troy_intro = result.get('troy_intro')
    if troy_intro and result.get('has_troy_mcclure'):
        existing_note = ep.get('notes') or ''
        # Only append if not already in the note
        if 'troy mcclure' not in existing_note.lower() and \
           'you may remember me from' not in existing_note.lower():
            if existing_note:
                ep['notes'] = existing_note.rstrip('.') + '. ' + troy_intro
            else:
                ep['notes'] = troy_intro
            changed = True

    # Report
    parts = []
    if result.get('has_lionel_hutz'):  parts.append('Hutz')
    if result.get('has_troy_mcclure'): parts.append('Troy')
    if not parts: parts.append('neither')
    status = '+'.join(parts)
    intro_preview = ''
    if troy_intro and result.get('has_troy_mcclure'):
        intro_preview = f' | "{troy_intro[:50]}..."'
    print(f'[{status}]{intro_preview}')

    return changed

def update_series_json():
    """Add troy_mcclure to simpsons_series.json character list."""
    path = os.path.join(BASE, 'simpsons_series.json')
    if not os.path.exists(path):
        print('  simpsons_series.json not found — skipping')
        return

    with open(path, encoding='utf-8') as f:
        data = json.load(f)

    chars = data.get('characters', [])
    ids   = [c['id'] for c in chars]

    if 'troy_mcclure' in ids:
        print('  troy_mcclure already in simpsons_series.json')
        return

    # Insert after lionel_hutz
    troy_entry = {
        'id':      'troy_mcclure',
        'name':    'Troy McClure',
        'portrait': './images/simpsons/characters/troy_mcclure.jpg'
    }

    try:
        idx = ids.index('lionel_hutz')
        chars.insert(idx + 1, troy_entry)
    except ValueError:
        chars.append(troy_entry)

    data['characters'] = chars
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print('  ✓ troy_mcclure added to simpsons_series.json')

def main():
    print('='*60)
    print('TROY McCLURE PATCH SCRIPT')
    print('='*60)

    if not ANTHROPIC_KEY:
        print('\nERROR: ANTHROPIC_API_KEY not set!')
        print('Set it with: export ANTHROPIC_API_KEY=sk-ant-...')
        return

    # Step 1: Update series JSON
    print('\n── Step 1: Updating simpsons_series.json ──')
    update_series_json()

    # Step 2: Process all era files
    total_processed = 0
    total_changed   = 0
    troy_episodes   = []

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
            changed = process_episode(ep)
            if changed:
                total_changed += 1
                file_changed = True
            if ep.get('characters') and 'troy_mcclure' in ep['characters']:
                troy_episodes.append(f"S{ep['season']:02d}E{ep['episode']:02d} — {ep['title']}")
            total_processed += 1

            # Save every 25 episodes
            if total_processed % 25 == 0 and file_changed:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

            time.sleep(0.3)

        if file_changed:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f'  ✓ Saved {era_file}')

    # Summary
    print(f'\n{"="*60}')
    print('TROY McCLURE PATCH COMPLETE')
    print(f'  Episodes checked: {total_processed}')
    print(f'  Episodes updated: {total_changed}')
    print(f'\nTroy McClure appearances ({len(troy_episodes)} total):')
    for ep in troy_episodes:
        print(f'  {ep}')
    print('='*60)

if __name__ == '__main__':
    main()
