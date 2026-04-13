#!/usr/bin/env python3
"""
Gray Video Vault — Generate Guest Image Manifest
Scans images/simpsons/guests/ and writes simpsons_guests_manifest.json
listing only guests that have valid image files.
The GHOF mosaic uses this to skip guests with no photo.

Run from the TV Vault folder after downloading guest images.
Usage: python3 generate_guest_manifest.py
"""

import os, json, re

BASE       = os.path.dirname(os.path.abspath(__file__))
GUEST_DIR  = os.path.join(BASE, 'images', 'simpsons', 'guests')
OUT        = os.path.join(BASE, 'simpsons_guests_manifest.json')

ERA_FILES = [
    'simpsons_golden.json',
    'simpsons_classic.json',
    'simpsons_middle.json',
    'simpsons_modern_a.json',
    'simpsons_modern_b.json',
]

MAIN_CAST = {
    'Dan Castellaneta', 'Julie Kavner', 'Nancy Cartwright',
    'Yeardley Smith', 'Hank Azaria', 'Harry Shearer'
}

def actor_fname(name):
    return re.sub(r'[^a-z0-9]+', '_', name.lower().strip()).strip('_') + '.jpg'

def main():
    print('Scanning guest image folder...')

    # Get all valid image files
    if not os.path.exists(GUEST_DIR):
        print(f'Guest folder not found: {GUEST_DIR}')
        return

    valid_files = set()
    for fname in os.listdir(GUEST_DIR):
        if not fname.endswith('.jpg'): continue
        path = os.path.join(GUEST_DIR, fname)
        if os.path.getsize(path) < 1000: continue
        # Verify it's a real JPEG
        with open(path, 'rb') as f:
            header = f.read(2)
        if header == b'\xff\xd8':
            valid_files.add(fname)

    print(f'Found {len(valid_files)} valid guest images')

    # Build guest map to get appearance counts
    guest_map = {}
    for era_file in ERA_FILES:
        path = os.path.join(BASE, era_file)
        if not os.path.exists(path): continue
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        for ep in data.get('episodes', []):
            for g in (ep.get('guests') or []):
                actor = (g.get('actor') or '').strip()
                char  = (g.get('character') or '').strip()
                if not actor or actor in MAIN_CAST: continue
                if not char or char.lower() in ('voice','narrator','various'): continue
                if actor not in guest_map: guest_map[actor] = 0
                guest_map[actor] += 1

    # Build manifest — only guests with valid image files
    manifest = []
    for actor, count in sorted(guest_map.items(), key=lambda x: x[1], reverse=True):
        fname = actor_fname(actor)
        if fname in valid_files:
            manifest.append({
                'actor': actor,
                'file':  f'./images/simpsons/guests/{fname}',
                'eps':   count
            })

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f'Manifest written: {len(manifest)} guests with images')
    print(f'Output: simpsons_guests_manifest.json')
    print('\nNow drop simpsons_guests_manifest.json into your TV Vault folder')
    print('and hard refresh — the GHOF montage will use only available photos.')

if __name__ == '__main__':
    main()
