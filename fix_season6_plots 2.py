#!/usr/bin/env python3
"""
fix_season6_plots.py
Generates AI plot summaries for Season 6 Seinfeld episodes.
Run from the TV Vault folder after setting ANTHROPIC_API_KEY.
"""
import json, os, time
import anthropic

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE, 'seinfeld_data.json')

print('Loading seinfeld_data.json...')
with open(DATA_FILE, encoding='utf-8') as f:
    data = json.load(f)

s6_eps = [ep for ep in data['episodes'] if ep['season'] == 6]
print(f'Found {len(s6_eps)} Season 6 episodes')

client = anthropic.Anthropic()

for i, ep in enumerate(s6_eps):
    desc = ep.get('tmdb_description', '')
    if not desc:
        print(f'  [{i+1}/{len(s6_eps)}] {ep["title"]} — no description, skipping')
        continue

    print(f'  [{i+1}/{len(s6_eps)}] {ep["title"]}...')

    prompt = f"""Seinfeld episode "{ep['title']}" (Season {ep['season']}, Episode {ep['episode']}).
Air date: {ep.get('air_date', 'unknown')}.
Overview: {desc}

Write a single sentence (max 25 words) describing what each main character does in this episode.
Only include characters who have a meaningful role. If a character barely appears, omit them.
Respond in this exact JSON format with no other text:
{{"jerry": "...", "george": "...", "elaine": "...", "kramer": "..."}}
Use null for any character with no meaningful role."""

    try:
        msg = client.messages.create(
            model='claude-opus-4-5',
            max_tokens=300,
            messages=[{'role': 'user', 'content': prompt}]
        )
        raw = msg.content[0].text.strip()
        plots_raw = json.loads(raw)
        plots = {k: v for k, v in plots_raw.items() if v and v != 'null'}
        ep['plots'] = plots
        print(f'    Plots: {list(plots.keys())}')
    except Exception as e:
        print(f'    Error: {e}')
        ep['plots'] = {}

    time.sleep(1)

with open(DATA_FILE, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f'\n✓ Done! Plot summaries added to Season 6 episodes.')

# Sanity check
filled = sum(1 for ep in s6_eps if ep.get('plots'))
print(f'  Episodes with plots: {filled}/{len(s6_eps)}')
