#!/usr/bin/env python3
"""
Gray Video Vault — Image Health Check
Scans all image files and identifies corrupted/truncated ones
that would cause Netlify deploy failures.

Run from the TV Vault folder.
Usage: python3 check_images.py
   or: python3 check_images.py --fix   (deletes bad files automatically)
"""

import os, sys, struct

BASE       = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR  = os.path.join(BASE, 'images')
FIX_MODE   = '--fix' in sys.argv

def check_jpeg(path):
    """Returns (ok, reason) for a JPEG file."""
    try:
        size = os.path.getsize(path)
        if size == 0:
            return False, 'empty file'
        if size < 100:
            return False, f'too small ({size} bytes)'
        with open(path, 'rb') as f:
            header = f.read(2)
            if header != b'\xff\xd8':
                if header[:4] == b'\x89PNG':
                    return False, 'PNG saved as .jpg'
                return False, f'not a JPEG (header: {header.hex()})'
            # Check file ends with JPEG end-of-image marker
            f.seek(-2, 2)
            trailer = f.read(2)
            if trailer != b'\xff\xd9':
                return False, f'truncated/incomplete JPEG'
        return True, 'ok'
    except Exception as e:
        return False, f'read error: {e}'

def check_png(path):
    """Returns (ok, reason) for a PNG file."""
    try:
        size = os.path.getsize(path)
        if size == 0:
            return False, 'empty file'
        if size < 100:
            return False, f'too small ({size} bytes)'
        with open(path, 'rb') as f:
            header = f.read(8)
            if header[:4] != b'\x89PNG':
                return False, 'not a PNG'
            # Check PNG ends with IEND chunk
            f.seek(-12, 2)
            trailer = f.read(4)
            if trailer != b'IEND':
                return False, 'truncated/incomplete PNG'
        return True, 'ok'
    except Exception as e:
        return False, f'read error: {e}'

def main():
    print('='*60)
    print('IMAGE HEALTH CHECK')
    if FIX_MODE:
        print('FIX MODE — bad files will be deleted')
    print('='*60)

    if not os.path.exists(IMAGE_DIR):
        print(f'Images folder not found: {IMAGE_DIR}')
        return

    bad   = []
    good  = 0
    total = 0

    for root, dirs, files in os.walk(IMAGE_DIR):
        # Sort for consistent output
        for fname in sorted(files):
            ext = fname.lower().rsplit('.', 1)[-1] if '.' in fname else ''
            if ext not in ('jpg', 'jpeg', 'png', 'webp'):
                continue
            path = os.path.join(root, fname)
            total += 1

            if ext in ('jpg', 'jpeg'):
                ok, reason = check_jpeg(path)
            elif ext == 'png':
                ok, reason = check_png(path)
            else:
                ok, reason = True, 'ok'  # skip webp deep check

            if ok:
                good += 1
            else:
                rel = os.path.relpath(path, BASE)
                bad.append((rel, reason))

    print(f'\nScanned {total} image files')
    print(f'  Good: {good}')
    print(f'  Bad:  {len(bad)}')

    if bad:
        print(f'\nProblematic files:')
        for rel, reason in bad:
            print(f'  [{reason}]  {rel}')

        if FIX_MODE:
            print(f'\nDeleting {len(bad)} bad files...')
            deleted = 0
            for rel, reason in bad:
                full = os.path.join(BASE, rel)
                try:
                    os.remove(full)
                    print(f'  Deleted: {rel}')
                    deleted += 1
                except Exception as e:
                    print(f'  Failed to delete {rel}: {e}')
            print(f'\n{deleted} files deleted.')
            print('You can now retry the Netlify deploy.')
        else:
            print(f'\nRun with --fix to automatically delete bad files:')
            print(f'  python3 check_images.py --fix')
    else:
        print('\nAll images look good — Netlify deploy should work!')

    print('='*60)

if __name__ == '__main__':
    main()
