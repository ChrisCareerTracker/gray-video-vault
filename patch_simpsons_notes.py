#!/usr/bin/env python3
"""
Gray Video Vault — Springfield Notes Patcher
Adds a 'notes' field to every episode in the Simpsons JSON files.
Notes are curated facts: debut appearances, behind-the-scenes details,
cultural impact moments, iconic characters, uncredited guests, etc.

Run AFTER all enrichment scripts have completed.
Run from the TV Vault folder (same location as index.html).

Usage: python3 patch_simpsons_notes.py
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

def anthropic_note(ep):
    """Get a Springfield Note for one episode. Returns string or None."""
    if not ANTHROPIC_KEY:
        return None

    prompt = f"""You are a Simpsons expert and TV historian. Write a single Springfield Note for this episode.

Episode: S{ep['season']:02d}E{ep['episode']:02d} — "{ep['title']}"
Air date: {ep.get('air_date', 'unknown')}
Description: {ep.get('description', '')}
Classic: {ep.get('classic', False)}
Musical: {ep.get('musical', False)}
Parody: {ep.get('parody', False)}
Parody of: {ep.get('parody_of', '')}
Treehouse of Horror: {ep.get('treehouse_of_horror', False)}

A Springfield Note is a single punchy 1-2 sentence fact that makes this episode memorable or historically significant. Good examples:
- "First appearance of Sideshow Bob, who would go on to appear in 14 more episodes."
- "Michael Jackson guest starred uncredited under the pseudonym 'John Jay Smith.'"
- "The monorail song by Conan O'Brien became one of the most quoted moments in the show's history."
- "Dustin Hoffman insisted on the pseudonym Sam Etic — a play on 'semantic' — in the credits."
- "This episode introduced the phrase 'D'oh!' to the Oxford English Dictionary."
- "First of six appearances by Kelsey Grammer as Sideshow Bob."
- "The Cape Fear parody required special licensing — one of the most expensive episodes to produce at the time."
- "Features the only appearance of Frank Grimes, whose tragic story became a fan touchstone for the show's shift in tone."

Focus on: character debuts, notable guest star facts, cultural milestones, production trivia, record-breaking achievements, phrases that entered the lexicon, one-time iconic characters, behind-the-scenes stories.

RULES:
- Return ONLY the note text — no quotes, no label, no preamble
- Maximum 2 sentences
- Be specific and factual — no vague praise like "a fan favorite"
- If there is genuinely nothing notable to say, return exactly: null
- Never invent facts you are not confident about — return null instead"""

    headers = {
        'x-api-key': ANTHROPIC_KEY,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json'
    }
    body = {
        'model': 'claude-sonnet-4-20250514',
        'max_tokens': 150,
        'messages': [{'role': 'user', 'content': prompt}]
    }

    for attempt in range(3):
        try:
            r = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers=headers, json=body, timeout=30
            )
            if r.status_code == 401:
                print('  ERROR: Anthropic API key invalid (401). Check your key.')
                return None
            if r.status_code == 429:
                print('  Anthropic rate limit — waiting 15s...')
                time.sleep(15)
                continue
            r.raise_for_status()
            text = r.json()['content'][0]['text'].strip()
            # Strip any accidental quotes or markdown
            text = re.sub(r'^["\']|["\']$', '', text).strip()
            if text.lower() == 'null' or text == '':
                return None
            return text
        except Exception as e:
            if attempt == 2:
                print(f'    API error: {e}')
                return None
            time.sleep(5)
    return None

def main():
    print('='*60)
    print('SPRINGFIELD NOTES PATCHER')
    print('='*60)

    if not ANTHROPIC_KEY:
        print('\nERROR: ANTHROPIC_API_KEY not set!')
        print('Set it with: export ANTHROPIC_API_KEY=sk-ant-...')
        print('Then re-run this script.')
        return

    total_processed = 0
    total_noted     = 0
    total_null      = 0
    total_skipped   = 0

    for era_file in ERA_FILES:
        path = os.path.join(BASE, era_file)
        if not os.path.exists(path):
            print(f'\nSkipping {era_file} — not found')
            continue

        with open(path, encoding='utf-8') as f:
            data = json.load(f)

        episodes  = data.get('episodes', [])
        era_label = data.get('era_label', era_file)
        print(f'\n── {era_label} ({len(episodes)} episodes) ──')

        changed = False
        era_noted = 0
        era_null  = 0
        era_skip  = 0

        for i, ep in enumerate(episodes):
            code = f"S{ep['season']:02d}E{ep['episode']:02d}"

            # Skip if already has a note (re-run safe)
            if ep.get('notes') is not None:
                era_skip += 1
                total_skipped += 1
                continue

            print(f'  {code} — {ep["title"][:45]}...', end=' ', flush=True)

            note = anthropic_note(ep)
            ep['notes'] = note
            changed = True
            total_processed += 1

            if note:
                era_noted += 1
                total_noted += 1
                # Show a preview
                preview = note[:70] + ('...' if len(note) > 70 else '')
                print(f'✓ "{preview}"')
            else:
                era_null += 1
                total_null += 1
                print('— (no note)')

            # Polite rate limiting
            time.sleep(0.4)

            # Save progress every 25 episodes in case of interruption
            if total_processed % 25 == 0:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f'  [Progress saved — {total_processed} processed so far]')

        # Final save for this era file
        if changed:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f'  ✓ Saved {era_file}')

        print(f'  Era totals: {era_noted} notes · {era_null} null · {era_skip} already done')

    print(f'\n{"="*60}')
    print('SPRINGFIELD NOTES COMPLETE')
    print(f'  Notes written: {total_noted}')
    print(f'  No note (null): {total_null}')
    print(f'  Already had note (skipped): {total_skipped}')
    print(f'  Total processed this run: {total_processed}')
    print(f'\nNext step: come back to Claude to build the new episode modal!')
    print('='*60)

if __name__ == '__main__':
    main()
