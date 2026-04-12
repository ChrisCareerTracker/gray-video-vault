#!/usr/bin/env python3
"""Fix Tasmanian Devil image path from .jpg to .png"""

import os, json

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, 'looney_tunes_characters.json')

with open(path, encoding='utf-8') as f:
    data = json.load(f)

fixed = False
for char in data.get('characters', []):
    if 'tasmanian' in char.get('id', '').lower() or 'tasmanian' in char.get('name', '').lower():
        old = char.get('image_url', '')
        new = old.replace('tasmanian-devil.jpg', 'tasmanian-devil.png')
        char['image_url'] = new
        print(f"Fixed: {old} -> {new}")
        fixed = True

if fixed:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("Saved!")
else:
    print("Tasmanian Devil entry not found")
