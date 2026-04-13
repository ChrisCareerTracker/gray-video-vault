#!/usr/bin/env python3
"""
Simpsons Character Re-Enrichment Script
Re-tags all 790 episodes across 5 era files with accurate character IDs.
Uses Claude Haiku for speed and cost efficiency.

Usage:
  export ANTHROPIC_API_KEY=sk-ant-...
  python3 enrich_simpsons_characters.py

Run from the TV Vault folder (drag into Terminal).
Output files are written alongside the originals with _chars suffix first,
then you confirm and they overwrite the originals.
"""

import json
import os
import time
import re
import urllib.request

API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
if not API_KEY:
    print('ERROR: ANTHROPIC_API_KEY not set. Run: export ANTHROPIC_API_KEY=sk-ant-...')
    exit(1)

ERA_FILES = [
    'simpsons_golden.json',
    'simpsons_classic.json',
    'simpsons_middle.json',
    'simpsons_modern_a.json',
    'simpsons_modern_b.json',
]

# All valid character IDs — must match simpsons_series.json exactly
VALID_CHARS = [
    'homer', 'marge', 'bart', 'lisa', 'maggie', 'grandpa', 'burns', 'flanders',
    'moe', 'milhouse', 'krusty', 'sideshow_bob', 'apu', 'barney', 'wiggum',
    'skinner', 'smithers', 'ralph', 'nelson', 'lenny_carl', 'fat_tony', 'snake',
    'comic_book_guy', 'sideshow_mel', 'patty_selma', 'lionel_hutz', 'troy_mcclure',
    'chalmers', 'kent_brockman', 'dr_nick', 'professor_frink', 'cletus', 'dr_hibbert',
    'mayor_quimby', 'rainier_wolfcastle', 'herbert_powell', 'otto', 'willie',
    'rod_todd', 'bleeding_gums'
]

VALID_SET = set(VALID_CHARS)

SYSTEM_PROMPT = """You are an expert on The Simpsons TV series. Your job is to tag episodes with the recurring characters who have a meaningful speaking or visible presence in that episode.

You will be given episode information and must return ONLY a JSON array of character IDs from the provided list.

Rules:
- Only include characters who actually appear and have a meaningful role (speaking lines or significant screen time)
- Homer, Marge, Bart, Lisa appear in almost every episode — include them unless the description clearly indicates they don't
- Maggie rarely speaks but often appears — include her when mentioned
- Do NOT include characters just because they're regulars — only if they appear in this specific episode
- DO include recurring characters like Ned Flanders, Mr. Burns, Wiggum etc. when they appear
- herbert_powell = Herb Powell (Homer's half-brother, appears in S2E15 and S3E24)
- otto = Otto the school bus driver
- willie = Groundskeeper Willie
- rod_todd = Rod and Todd Flanders
- bleeding_gums = Bleeding Gums Murphy (jazz musician, Lisa's mentor)
- lenny_carl = Lenny and Carl together
- patty_selma = Patty and Selma Bouvier
- Return ONLY a valid JSON array, nothing else. Example: ["homer","marge","bart","burns"]"""


def call_claude(title, season, episode, description, guests, notes):
    guest_names = [g.get('actor', '') for g in (guests or [])][:8]
    guest_str = ', '.join(guest_names) if guest_names else 'None'

    user_prompt = (
        'Episode: S' + str(season).zfill(2) + 'E' + str(episode).zfill(2) +
        ' - ' + title + '\n' +
        'Description: ' + (description or 'No description')[:400] + '\n' +
        'Guest stars: ' + guest_str + '\n' +
        ('Springfield Notes: ' + notes[:200] + '\n' if notes else '') +
        '\nValid character IDs: ' + json.dumps(VALID_CHARS) + '\n\n' +
        'Return ONLY a JSON array of character IDs who appear in this episode.'
    )

    payload = json.dumps({
        'model': 'claude-haiku-4-5',
        'max_tokens': 200,
        'system': SYSTEM_PROMPT,
        'messages': [{'role': 'user', 'content': user_prompt}]
    }).encode('utf-8')

    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=payload,
        headers={
            'x-api-key': API_KEY,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json'
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            text = data['content'][0]['text'].strip()
            # Extract JSON array from response
            match = re.search(r'\[.*?\]', text, re.DOTALL)
            if match:
                raw = json.loads(match.group())
                # Filter to only valid IDs
                return [c for c in raw if c in VALID_SET]
            return []
    except Exception as e:
        print('    API error: ' + str(e))
        return None


def process_file(filename):
    if not os.path.exists(filename):
        print('SKIPPING ' + filename + ' — file not found')
        return

    print('\n' + '='*60)
    print('Processing: ' + filename)

    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)

    episodes = data['episodes']
    total = len(episodes)
    updated = 0
    errors = 0

    for i, ep in enumerate(episodes):
        season = ep.get('season', 0)
        episode = ep.get('episode', 0)
        title = ep.get('title', 'Unknown')
        code = 'S' + str(season).zfill(2) + 'E' + str(episode).zfill(2)

        print('  [' + str(i+1) + '/' + str(total) + '] ' + code + ' - ' + title[:45], end='', flush=True)

        result = call_claude(
            title=title,
            season=season,
            episode=episode,
            description=ep.get('description', ''),
            guests=ep.get('guests', []),
            notes=ep.get('notes', '')
        )

        if result is None:
            print(' ERROR — keeping existing')
            errors += 1
            time.sleep(2)
        else:
            old = ep.get('characters', [])
            ep['characters'] = result
            ep['_chars_v2'] = True
            updated += 1
            print(' → ' + str(result[:4]) + ('...' if len(result) > 4 else ''))

        # Rate limiting — Haiku is fast but be respectful
        time.sleep(0.3)

    # Write output
    out_file = filename.replace('.json', '_retagged.json')
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print('\n  Done: ' + str(updated) + ' episodes tagged, ' + str(errors) + ' errors')
    print('  Written to: ' + out_file)
    return out_file


def main():
    print('Simpsons Character Re-Enrichment')
    print('Model: claude-haiku-4-5')
    print('Episodes: 790 across 5 era files')
    print('Estimated cost: ~$0.28')
    print()

    confirm = input('Proceed? (y/n): ').strip().lower()
    if confirm != 'y':
        print('Aborted.')
        return

    output_files = []
    for era_file in ERA_FILES:
        out = process_file(era_file)
        if out:
            output_files.append((era_file, out))

    print()
    print('='*60)
    print('ALL DONE')
    print()
    print('Output files written (with _retagged suffix):')
    for original, output in output_files:
        print('  ' + output)

    print()
    print('To replace originals, run these commands:')
    for original, output in output_files:
        print('  mv ' + output + ' ' + original)

    print()
    print('Then hard refresh your local server (Cmd+Shift+R) to verify.')


if __name__ == '__main__':
    main()
