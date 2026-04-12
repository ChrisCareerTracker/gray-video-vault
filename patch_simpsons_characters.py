#!/usr/bin/env python3
"""
Gray Video Vault — Simpsons Character Re-Enrichment Script
Re-tags character appearances for all 34 characters using improved prompts.
Uses episode title + description + Springfield Notes for better accuracy.

Overwrites ONLY the 'characters' field — all other fields untouched.
Re-run safe: tracks progress, saves every 25 episodes.

Run from the TV Vault folder.
Usage: python3 patch_simpsons_characters.py
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

# All 34 characters with descriptions to help the AI identify them
CHARACTER_GUIDE = """
Return a JSON array containing ONLY the IDs of characters who have a meaningful 
speaking role or are central to a plot in this episode. Use this ID reference:

homer           — Homer Simpson (main cast, only include if he has a notable subplot)
marge           — Marge Simpson (main cast, only include if she has a notable subplot)  
bart            — Bart Simpson (main cast, only include if he has a notable subplot)
lisa            — Lisa Simpson (main cast, only include if she has a notable subplot)
maggie          — Maggie Simpson (only include if Maggie has actual plot significance)
burns           — Mr. Burns / C. Montgomery Burns
flanders        — Ned Flanders
moe             — Moe Szyslak (bartender)
milhouse        — Milhouse Van Houten
krusty          — Krusty the Clown / Herschel Krustofsky
sideshow_bob    — Sideshow Bob / Robert Terwilliger (voiced by Kelsey Grammer)
apu             — Apu Nahasapeemapetilon (Kwik-E-Mart)
barney          — Barney Gumble
wiggum          — Chief Wiggum / Clancy Wiggum
skinner         — Principal Skinner / Seymour Skinner
smithers        — Waylon Smithers
ralph           — Ralph Wiggum
nelson          — Nelson Muntz
lenny_carl      — Lenny Leonard or Carl Carlson (or both)
grandpa         — Grampa Simpson / Abraham Simpson / Abe
fat_tony        — Fat Tony / Marion Anthony D'Amico (mob boss, voiced by Joe Mantegna)
snake           — Snake Jailbird (recurring criminal)
comic_book_guy  — Comic Book Guy / Jeff Albertson
sideshow_mel    — Sideshow Mel (Krusty's sidekick with bone in hair)
patty_selma     — Patty Bouvier or Selma Bouvier (or both, Marge's sisters)
lionel_hutz     — Lionel Hutz (incompetent lawyer, voiced by Phil Hartman)
chalmers        — Superintendent Chalmers (Skinner's boss)
kent_brockman   — Kent Brockman (TV news anchor)
dr_nick         — Dr. Nick Riviera ("Hi everybody!")
professor_frink — Professor Frink (scientist)
cletus          — Cletus Spuckler (slack-jawed yokel)
dr_hibbert      — Dr. Julius Hibbert (family doctor)
mayor_quimby    — Mayor Quimby / "Diamond" Joe Quimby
rainier_wolfcastle — Rainier Wolfcastle / McBain (action movie star)
"""

def anthropic_characters(ep):
    """Re-tag character appearances for one episode."""
    if not ANTHROPIC_KEY:
        return None

    notes_line = f'Springfield Note: {ep["notes"]}' if ep.get('notes') else ''
    guests_line = ''
    if ep.get('guests'):
        guest_str = ', '.join([
            f"{g.get('actor','')} as {g.get('character','')}"
            for g in ep['guests'][:10] if g.get('actor')
        ])
        if guest_str:
            guests_line = f'Guest cast: {guest_str}'

    prompt = f"""You are a Simpsons expert. Identify which recurring characters appear in this episode.

Episode: S{ep['season']:02d}E{ep['episode']:02d} — "{ep['title']}"
Description: {ep.get('description','No description.')}
{notes_line}
{guests_line}

{CHARACTER_GUIDE}

RULES:
- For the main Simpson family (homer, marge, bart, lisa), ONLY include them if they have a significant individual subplot or the episode is primarily focused on them. Do NOT include them just because they appear in every episode.
- For ALL other characters, include them if they have any speaking role or meaningful scene.
- Be thorough — err on the side of including characters rather than excluding them.
- If a character is mentioned in the guest cast or Springfield Note, they almost certainly should be included.
- Return ONLY a valid JSON array of ID strings, nothing else. Example: ["burns","smithers","lionel_hutz"]
- If no recurring characters appear beyond the main family, return: []"""

    headers = {
        'x-api-key': ANTHROPIC_KEY,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json'
    }
    body = {
        'model': 'claude-sonnet-4-20250514',
        'max_tokens': 200,
        'messages': [{'role': 'user', 'content': prompt}]
    }

    VALID_IDS = {
        'homer','marge','bart','lisa','maggie','burns','flanders','moe',
        'milhouse','krusty','sideshow_bob','apu','barney','wiggum','skinner',
        'smithers','ralph','nelson','lenny_carl','grandpa','fat_tony','snake',
        'comic_book_guy','sideshow_mel','patty_selma','lionel_hutz','chalmers',
        'kent_brockman','dr_nick','professor_frink','cletus','dr_hibbert',
        'mayor_quimby','rainier_wolfcastle'
    }

    for attempt in range(3):
        try:
            r = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers=headers, json=body, timeout=30
            )
            if r.status_code == 401:
                print('\n  ERROR: Anthropic API key invalid (401).')
                return None
            if r.status_code == 429:
                print('  Rate limit — waiting 15s...')
                time.sleep(15)
                continue
            r.raise_for_status()
            text = r.json()['content'][0]['text'].strip()
            # Strip markdown fences if present
            text = re.sub(r'^```[a-z]*\n?', '', text)
            text = re.sub(r'\n?```$', '', text)
            parsed = json.loads(text)
            if not isinstance(parsed, list):
                return []
            # Validate — only keep known IDs
            return [c for c in parsed if c in VALID_IDS]
        except json.JSONDecodeError:
            return []
        except Exception as e:
            if attempt == 2:
                print(f'\n    API error: {e}')
                return None
            time.sleep(5)
    return None

def main():
    print('='*60)
    print('SIMPSONS CHARACTER RE-ENRICHMENT')
    print('='*60)

    if not ANTHROPIC_KEY:
        print('\nERROR: ANTHROPIC_API_KEY not set!')
        print('Set it with: export ANTHROPIC_API_KEY=sk-ant-...')
        return

    total_processed = 0
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

        for ep in episodes:
            code = f"S{ep['season']:02d}E{ep['episode']:02d}"

            # Skip if already re-enriched (marked with _chars_v2 flag)
            if ep.get('_chars_v2'):
                total_skipped += 1
                continue

            print(f'  {code} {ep["title"][:40]:<40}', end=' ', flush=True)

            chars = anthropic_characters(ep)

            if chars is None:
                # API error — skip and continue, don't mark as done
                print('! (API error, will retry on next run)')
                time.sleep(2)
                continue

            old_chars = ep.get('characters', [])
            ep['characters']  = chars
            ep['_chars_v2']   = True   # Mark as re-enriched
            changed = True
            total_processed += 1

            # Show what changed
            added   = [c for c in chars if c not in old_chars]
            removed = [c for c in old_chars if c not in chars]
            parts = []
            if added:   parts.append(f'+{",".join(added)}')
            if removed: parts.append(f'-{",".join(removed)}')
            change_str = '  '.join(parts) if parts else '(no change)'
            print(f'[{len(chars)}] {change_str}')

            time.sleep(0.4)

            # Save progress every 25 episodes
            if total_processed % 25 == 0:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f'  [Saved — {total_processed} processed]')

        # Final save
        if changed:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f'  ✓ {era_file} saved')

    print(f'\n{"="*60}')
    print('CHARACTER RE-ENRICHMENT COMPLETE')
    print(f'  Processed this run: {total_processed}')
    print(f'  Already done (skipped): {total_skipped}')
    print(f'\nCome back to Claude — character filters will now be accurate!')
    print('='*60)

if __name__ == '__main__':
    main()
