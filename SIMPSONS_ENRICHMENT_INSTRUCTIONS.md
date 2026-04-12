# SIMPSONS ENRICHMENT — STEP BY STEP INSTRUCTIONS
Gray Video Vault · One-time setup session

---

## BEFORE YOU START (do these once, not at your computer yet)

1. Go to console.anthropic.com
2. Sign in → click "API Keys" in the left sidebar
3. Click "Create Key" — name it "GVV Simpsons" so you know what it's for
4. Copy the key — it starts with sk-ant-api03-...
5. Paste it somewhere safe (Notes app) — you can only see it once

---

## STEP 1 — Copy the scripts into your TV Vault folder

Take all 7 files from your download and copy them into your
"TV Vault New Index and Json folders" folder in Dropbox:

  preflight_check.py
  enrich_simpsons_golden.py
  enrich_simpsons_classic.py
  enrich_simpsons_middle.py
  enrich_simpsons_modern_a.py
  enrich_simpsons_modern_b.py
  generate_simpsons_series.py

---

## STEP 2 — Move the folder to your Desktop

In Finder, find "TV Vault New Index and Json folders" in your Dropbox.
Drag it to your Desktop.

⚠️  Your local server (localhost:8000) will stop working while the
    folder is on the Desktop. That's fine — don't worry about it.

---

## STEP 3 — Open a fresh Terminal window

Press Cmd+N to open a brand new Terminal window.
(Cmd+N, not Cmd+T — a new window, not a new tab. This matters.)

---

## STEP 4 — Navigate into the folder

In Terminal, type exactly this (include the space after cd):

  cd [space]

Do NOT press Enter yet.

Now go to your Desktop in Finder, find the folder, and
drag the folder icon directly into the Terminal window.

The path will appear after "cd ". NOW press Enter.

To verify it worked, type:
  ls index.html

And press Enter. You should see:   index.html

If you see "No such file or directory" — something went wrong.
Close Terminal (Cmd+Q), reopen it (Cmd+N), and try Step 4 again.

---

## STEP 5 — Set your Anthropic API key

Type exactly this in Terminal, replacing YOUR_KEY_HERE with your key
(the sk-ant-api03-... string you copied in "Before You Start"):

  export ANTHROPIC_API_KEY=YOUR_KEY_HERE

Then press Enter.

⚠️  IMPORTANT RULES FOR PASTING THE KEY:
    - No spaces anywhere in the key
    - No line breaks — it must be one continuous string
    - No quotes around it
    - Copy it fresh from Notes — don't retype it

Example of what it should look like:
  export ANTHROPIC_API_KEY=sk-ant-api03-abc123xyz...

---

## STEP 6 — Run the pre-flight check

Type this and press Enter:
  python3 preflight_check.py

You should see green checkmarks (✓) next to all 5 items:
  ✓ Python version
  ✓ requests package
  ✓ TMDB API access
  ✓ Anthropic API key
  ✓ Working directory / index.html found

If you see a ✗ next to anything, read the fix instructions it prints
and resolve it before going further.

Common fixes:
  - requests not installed: python3 -m pip install requests
  - ANTHROPIC_API_KEY not set: redo Step 5
  - index.html not found: redo Step 4 (you're in the wrong folder)

---

## STEP 7 — Run the enrichment scripts in order

Run each script, wait for it to finish, then run the next.
Each script will print progress as it runs.

SCRIPT 1 — Golden Age (Seasons 1–8, ~172 episodes)
Estimated time: 15–25 minutes
  python3 enrich_simpsons_golden.py
Wait for: "DONE — X episodes written to simpsons_golden.json"

SCRIPT 2 — Classic Era (Seasons 9–12, ~88 episodes)
Estimated time: 8–15 minutes
  python3 enrich_simpsons_classic.py
Wait for: "DONE — X episodes written to simpsons_classic.json"

SCRIPT 3 — Middle Years (Seasons 13–20, ~176 episodes)
Estimated time: 15–25 minutes
  python3 enrich_simpsons_middle.py
Wait for: "DONE — X episodes written to simpsons_middle.json"

SCRIPT 4 — Modern Era A (Seasons 21–28, ~176 episodes)
Estimated time: 15–25 minutes
  python3 enrich_simpsons_modern_a.py
Wait for: "DONE — X episodes written to simpsons_modern_a.json"

SCRIPT 5 — Modern Era B (Seasons 29–37, ~176 episodes)
Estimated time: 15–25 minutes
  python3 enrich_simpsons_modern_b.py
Wait for: "DONE — X episodes written to simpsons_modern_b.json"

SCRIPT 6 — Series Shell (runs in seconds)
  python3 generate_simpsons_series.py
Wait for: "DONE — simpsons_series.json written"

Total estimated time: 75–120 minutes.
You do NOT need to sit at your computer the whole time.
Start each script and come back when it's done.

---

## STEP 8 — Verify the output files

After all scripts finish, type this and press Enter:
  ls -lh simpsons_*.json

You should see 6 files, all with reasonable sizes:
  simpsons_golden.json    (roughly 500KB–1MB)
  simpsons_classic.json   (roughly 250–500KB)
  simpsons_middle.json    (roughly 500KB–1MB)
  simpsons_modern_a.json  (roughly 500KB–1MB)
  simpsons_modern_b.json  (roughly 500KB–1MB)
  simpsons_series.json    (small — under 50KB)

If any file is missing or suspiciously tiny (under 10KB),
that script may have failed silently. Re-run that script only.

---

## STEP 9 — Move the folder back to Dropbox

In Finder, drag "TV Vault New Index and Json folders" from your Desktop
back to its original Dropbox location.

Then double-click "Start Vault Server.command" to restart your
local server at http://localhost:8000.

---

## STEP 10 — Tell Claude you're done!

Come back here and let me know the scripts finished successfully.
At that point we build the actual hub in index.html — the fun part.

---

## IF SOMETHING GOES WRONG

### A script crashes partway through
Check what the error message says. Most common issues:

  "JSONDecodeError" — the AI returned bad JSON on one episode.
  The script will log it and continue. Not a big deal.

  "Connection timeout" — internet hiccup. Just re-run the script.
  It will overwrite and start fresh.

  "401 Unauthorized" from Anthropic — your key expired or is wrong.
  Go to console.anthropic.com, create a new key, and redo Step 5.

  "401 Unauthorized" from TMDB — the TMDB key stopped working.
  Tell Claude and we'll get a fresh one.

### Terminal says "Permission denied" when running a script
Type this and press Enter (replacing scriptname.py with the actual name):
  chmod +x scriptname.py
Then try running it again.

### You accidentally closed Terminal mid-run
Re-do Steps 3–5 to get back into the folder with the API key set.
Then re-run only the script that was interrupted (check which .json
files exist with: ls simpsons_*.json)

---

## NOTES

- The scripts are safe to re-run. They overwrite their output file.
- The ANTHROPIC_API_KEY export only lasts for your current Terminal
  session. If you close Terminal and reopen, you'll need to do Step 5
  again before running any scripts.
- All 6 JSON files need to be in the same folder as index.html
  when you deploy to Netlify.
