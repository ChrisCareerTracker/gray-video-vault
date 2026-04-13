#!/usr/bin/env python3
"""
enrich_seinfeld_plots.py
Gray Video Vault — Seinfeld Per-Character Plot Enrichment
----------------------------------------------------------
Uses the Anthropic API to generate per-character plot summaries
for each Seinfeld episode, based on TMDB descriptions + guest lists.

Also detects recurring characters from the guest lists.

Reads:  seinfeld_data.json  (from enrich_seinfeld.py)
Writes: seinfeld_data.json  (updated in place — backs up original first)
        seinfeld_plots_report.txt

Run from inside the "TV Vault New Index and Json folders" folder:
  python3 enrich_seinfeld_plots.py

Requirements:
  pip3 install anthropic
"""

import json
import os
import time
import copy

try:
    import anthropic
except ImportError:
    print("Missing dependency. Run this first:")
    print("  pip3 install anthropic")
    exit(1)

# ── CONFIG ────────────────────────────────────────────────────────────────────

INPUT_JSON   = "seinfeld_data.json"
OUTPUT_JSON  = "seinfeld_data.json"       # updated in place
BACKUP_JSON  = "seinfeld_data_backup.json"
REPORT_FILE  = "seinfeld_plots_report.txt"

# Delay between API calls (seconds) — stay well within rate limits
API_DELAY = 0.5

# Characters we track for plot blocks
MAIN_CHARS = ["jerry", "george", "elaine", "kramer"]

# ── RECURRING CHARACTER DETECTION ─────────────────────────────────────────────
# Maps character_id → list of strings to search for in guest/cast data

RECURRING_NAMES = {
    "newman":       ["Newman", "Wayne Knight"],
    "frank":        ["Frank Costanza", "Jerry Stiller"],
    "estelle":      ["Estelle Costanza", "Estelle Harris"],
    "steinbrenner": ["George Steinbrenner", "Larry David"],
    "peterman":     ["J. Peterman", "John O'Hurley"],
    "puddy":        ["David Puddy", "Patrick Warburton"],
    "uncle_leo":    ["Uncle Leo", "Len Lesser"],
    "morty":        ["Morty Seinfeld", "Barney Martin"],
    "helen":        ["Helen Seinfeld", "Liz Sheridan"],
    "jackie":       ["Jackie Chiles", "Phil Morris"],
    "tim_whatley":  ["Tim Whatley", "Bryan Cranston"],
    "bob_sacamano": ["Bob Sacamano"],
}

def detect_recurring(guests):
    """Return list of recurring character IDs present in guest list."""
    found = []
    search_text = " ".join(guests).lower()
    for char_id, names in RECURRING_NAMES.items():
        for name in names:
            if name.lower() in search_text:
                found.append(char_id)
                break
    return found

# ── PROMPT ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a Seinfeld expert writing concise per-character plot summaries 
for a fan collection website. You write in a punchy, wry tone that matches the show's voice.

Rules:
- Only include characters who have meaningful plot presence in the episode
- Each summary is exactly 1 sentence, max 25 words
- Write in present tense ("Jerry discovers...", "George lies about...")
- Be specific — name the actual situation, not vague generalities
- If a character barely appears, omit them entirely
- Return ONLY valid JSON, no other text, no markdown code fences"""

def build_prompt(ep):
    """Build the user prompt for a single episode."""
    guests_str = ", ".join(ep.get("tmdb_guests", [])[:10]) or "none listed"
    return f"""Episode: {ep['id']} — "{ep['nickname']}"
Air date: {ep['air_date']}
Description: {ep['tmdb_description']}
Guest cast: {guests_str}

Write per-character plot summaries for this episode. Return JSON in exactly this format:
{{
  "jerry": "One sentence about Jerry's storyline, or omit key if Jerry has no meaningful plot",
  "george": "One sentence about George's storyline, or omit key if George has no meaningful plot", 
  "elaine": "One sentence about Elaine's storyline, or omit key if Elaine has no meaningful plot",
  "kramer": "One sentence about Kramer's storyline, or omit key if Kramer has no meaningful plot"
}}

Only include keys for characters with real plot presence. Return JSON only."""

# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    report_lines = []

    def rpt(line):
        print(line)
        report_lines.append(line)

    rpt("=" * 70)
    rpt("SEINFELD PLOT ENRICHMENT REPORT")
    rpt("=" * 70)

    # Load existing data
    if not os.path.exists(INPUT_JSON):
        rpt(f"FATAL: {INPUT_JSON} not found. Run enrich_seinfeld.py first.")
        return

    with open(INPUT_JSON, encoding="utf-8") as f:
        data = json.load(f)

    episodes = data["episodes"]
    rpt(f"\nLoaded {len(episodes)} episodes from {INPUT_JSON}")

    # Back up original
    with open(BACKUP_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    rpt(f"Backup saved to {BACKUP_JSON}")

    # Initialize Anthropic client
    # API key is read from ANTHROPIC_API_KEY environment variable automatically
    client = anthropic.Anthropic()

    rpt(f"\n[PASS 1] Detecting recurring characters from guest lists...")
    recurring_counts = {k: 0 for k in RECURRING_NAMES}
    for ep in episodes:
        ep["recurring"] = detect_recurring(ep.get("tmdb_guests", []))
        for char_id in ep["recurring"]:
            if char_id in recurring_counts:
                recurring_counts[char_id] += 1

    rpt("  Recurring character episode counts:")
    for char_id, count in sorted(recurring_counts.items(), key=lambda x: -x[1]):
        rpt(f"    {char_id:<20} {count} episodes")

    rpt(f"\n[PASS 2] Generating per-character plot summaries via Claude API...")
    rpt(f"  Processing {len(episodes)} episodes (~{len(episodes) * API_DELAY / 60:.1f} min estimated)...\n")

    success = 0
    partial = 0
    failed  = 0
    skipped = 0

    for i, ep in enumerate(episodes):
        ep_id = ep["id"]
        nickname = ep["nickname"]
        desc = ep.get("tmdb_description", "")

        # Skip clip shows / episodes with no useful description
        if len(desc) < 30:
            ep["plots"] = {}
            skipped += 1
            rpt(f"  SKIP {ep_id} {nickname} — no description")
            continue

        # Build prompt and call API
        try:
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": build_prompt(ep)}]
            )

            raw = message.content[0].text.strip()

            # Strip markdown fences if model added them despite instructions
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            plots = json.loads(raw)

            # Validate — keep only recognized character keys with string values
            clean_plots = {}
            for char in MAIN_CHARS:
                if char in plots and isinstance(plots[char], str) and len(plots[char]) > 10:
                    clean_plots[char] = plots[char]

            ep["plots"] = clean_plots
            count = len(clean_plots)

            if count == 0:
                failed += 1
                rpt(f"  ✗ {ep_id} {nickname} — parsed but no valid plot blocks")
            elif count < 3:
                partial += 1
                chars = "/".join(clean_plots.keys())
                rpt(f"  ⚠ {ep_id} {nickname} — {count} plots ({chars})")
            else:
                success += 1
                if (i + 1) % 20 == 0:
                    rpt(f"  ... {i+1}/{len(episodes)} done")

        except json.JSONDecodeError as e:
            ep["plots"] = {}
            failed += 1
            rpt(f"  ✗ {ep_id} {nickname} — JSON parse error: {e} | raw: {raw[:100]}")
        except Exception as e:
            ep["plots"] = {}
            failed += 1
            rpt(f"  ✗ {ep_id} {nickname} — API error: {e}")

        time.sleep(API_DELAY)

    # ── RESULTS ───────────────────────────────────────────────────────────────

    rpt(f"\n[RESULTS]")
    rpt(f"  Full plots (3-4 chars):  {success}")
    rpt(f"  Partial plots (1-2):     {partial}")
    rpt(f"  Failed / no plots:       {failed}")
    rpt(f"  Skipped (no desc):       {skipped}")

    # Spot check a few famous episodes
    rpt(f"\n[SPOT CHECK — Famous Episodes]")
    spot_check = ["S04E11", "S07E06", "S05E14", "S09E10", "S08E19", "S09E03"]
    for ep in episodes:
        if ep["id"] in spot_check:
            rpt(f"\n  {ep['id']} {ep['nickname']}")
            for char, plot in ep.get("plots", {}).items():
                rpt(f"    {char.upper()}: {plot}")
            rpt(f"  Recurring: {ep.get('recurring', [])}")

    # ── SAVE ──────────────────────────────────────────────────────────────────

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    rpt(f"\n[OUTPUT]")
    rpt(f"  ✓ {OUTPUT_JSON} updated with plot data")
    rpt(f"  ✓ {REPORT_FILE} written")
    rpt(f"  (Original backed up to {BACKUP_JSON})")

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    rpt(f"\n[DONE]")
    rpt("Next step: upload updated seinfeld_data.json + seinfeld_plots_report.txt to Claude.")
    rpt("Then we build the hub in index.html.")

if __name__ == "__main__":
    main()
