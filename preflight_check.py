#!/usr/bin/env python3
"""
Gray Video Vault — Pre-Flight Check
Run this BEFORE starting the Simpsons enrichment scripts.
Verifies Python version, required packages, TMDB access, and Anthropic key.
"""

import sys, os, subprocess

TMDB_KEY = '573382ec2121f69d6a89fce35293591a'
TMDB_SERIES = 456

print('='*60)
print('GRAY VIDEO VAULT — PRE-FLIGHT CHECK')
print('='*60)

all_ok = True

# ── Python version ─────────────────────────────────────────────
print('\n1. Python version...')
v = sys.version_info
if v.major == 3 and v.minor >= 8:
    print(f'   ✓ Python {v.major}.{v.minor}.{v.micro}')
else:
    print(f'   ✗ Python {v.major}.{v.minor} found — need 3.8+')
    all_ok = False

# ── requests package ───────────────────────────────────────────
print('\n2. Required packages...')
try:
    import requests
    print(f'   ✓ requests {requests.__version__}')
except ImportError:
    print('   ✗ requests not installed')
    print('     Fix: pip3 install requests --break-system-packages')
    all_ok = False

# ── TMDB connectivity ──────────────────────────────────────────
print('\n3. TMDB API access...')
try:
    import requests as req
    r = req.get(
        f'https://api.themoviedb.org/3/tv/{TMDB_SERIES}',
        params={'api_key': TMDB_KEY},
        timeout=10
    )
    if r.status_code == 200:
        data = r.json()
        print(f'   ✓ TMDB connected — found: {data.get("name", "Unknown")}')
        print(f'   ✓ Total seasons on TMDB: {data.get("number_of_seasons", "?")}')
        print(f'   ✓ Total episodes on TMDB: {data.get("number_of_episodes", "?")}')
    else:
        print(f'   ✗ TMDB returned status {r.status_code}')
        all_ok = False
except Exception as e:
    print(f'   ✗ TMDB connection failed: {e}')
    all_ok = False

# ── Anthropic API key ──────────────────────────────────────────
print('\n4. Anthropic API key...')
anthropic_key = os.environ.get('ANTHROPIC_API_KEY', '')
if not anthropic_key:
    print('   ✗ ANTHROPIC_API_KEY not set')
    print('     Fix: export ANTHROPIC_API_KEY=sk-ant-...')
    print('     (paste your key after the = sign, no spaces)')
    all_ok = False
elif not anthropic_key.startswith('sk-ant-'):
    print(f'   ✗ Key looks wrong — should start with sk-ant-')
    print(f'     Got: {anthropic_key[:12]}...')
    all_ok = False
else:
    print(f'   Testing key: {anthropic_key[:16]}...')
    try:
        import requests as req
        r = req.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': anthropic_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json'
            },
            json={
                'model': 'claude-sonnet-4-20250514',
                'max_tokens': 10,
                'messages': [{'role': 'user', 'content': 'Say OK'}]
            },
            timeout=15
        )
        if r.status_code == 200:
            print('   ✓ Anthropic API key valid and working')
        elif r.status_code == 401:
            print('   ✗ Anthropic key rejected (401 Unauthorized)')
            print('     Create a new key at console.anthropic.com')
            all_ok = False
        elif r.status_code == 429:
            print('   ⚠ Anthropic key valid but rate limited (429)')
            print('     This is fine — the scripts handle rate limits automatically')
        else:
            print(f'   ✗ Anthropic returned status {r.status_code}')
            all_ok = False
    except Exception as e:
        print(f'   ✗ Anthropic connection failed: {e}')
        all_ok = False

# ── Output folder check ────────────────────────────────────────
print('\n5. Working directory...')
cwd = os.getcwd()
script_dir = os.path.dirname(os.path.abspath(__file__))
print(f'   Current directory: {cwd}')
print(f'   Script directory:  {script_dir}')
if cwd == script_dir:
    print('   ✓ Running from correct folder')
else:
    print('   ⚠ Running from a different folder than the scripts')
    print('     This is fine as long as you ran: cd [drag folder] Enter')

# Check for index.html as a sanity check
if os.path.exists(os.path.join(script_dir, 'index.html')):
    print('   ✓ index.html found — correct folder confirmed')
else:
    print('   ✗ index.html NOT found in this folder')
    print('     Make sure you dragged the "TV Vault New Index and Json folders" folder')
    all_ok = False

# ── Final verdict ──────────────────────────────────────────────
print('\n' + '='*60)
if all_ok:
    print('✓ ALL CHECKS PASSED — ready to run enrichment scripts!')
    print('\nRun them in this order:')
    print('  python3 enrich_simpsons_golden.py')
    print('  python3 enrich_simpsons_classic.py')
    print('  python3 enrich_simpsons_middle.py')
    print('  python3 enrich_simpsons_modern_a.py')
    print('  python3 enrich_simpsons_modern_b.py')
    print('  python3 generate_simpsons_series.py')
else:
    print('✗ ISSUES FOUND — fix the errors above before running scripts')
print('='*60)
