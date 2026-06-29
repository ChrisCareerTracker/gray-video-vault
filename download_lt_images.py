#!/usr/bin/env python3
"""
GVV Looney Tunes Image Downloader
Run from your Mac: python3 download_lt_images.py
Images will be saved to ./images/posters/ and ./images/backdrops/
Run this from inside your gray-video-vault repo folder.
"""

import urllib.request, urllib.parse, json, os, time

TMDB_KEY      = "573382ec2121f69d6a89fce35293591a"
TMDB_SEARCH   = "https://api.themoviedb.org/3/search/movie"
TMDB_MOVIE    = "https://api.themoviedb.org/3/movie"
TMDB_IMG_W500 = "https://image.tmdb.org/t/p/w500"
TMDB_IMG_W1280 = "https://image.tmdb.org/t/p/w1280"

os.makedirs("images/posters",   exist_ok=True)
os.makedirs("images/backdrops", exist_ok=True)

# tmdb_id of 0 = search by title/year; non-zero = fetch directly
new_cartoons = [
    {"title": "A Feud There Was",              "year": 1938, "tmdb_id": 0,      "poster_file": "A_Feud_There_Was_1938_poster.jpg",              "backdrop_file": "A_Feud_There_Was_1938_backdrop.jpg"},
    {"title": "Saddle Silly",                   "year": 1941, "tmdb_id": 0,      "poster_file": "Saddle_Silly_1941_poster.jpg",                   "backdrop_file": "Saddle_Silly_1941_backdrop.jpg"},
    {"title": "Coal Black and de Sebben Dwarfs","year": 1943, "tmdb_id": 0,      "poster_file": "Coal_Black_and_de_Sebben_Dwarfs_1943_poster.jpg","backdrop_file": "Coal_Black_and_de_Sebben_Dwarfs_1943_backdrop.jpg"},
    {"title": "Daffy Doodles",                  "year": 1946, "tmdb_id": 0,      "poster_file": "Daffy_Doodles_1946_poster.jpg",                  "backdrop_file": "Daffy_Doodles_1946_backdrop.jpg"},
    {"title": "Doggone Cats",                   "year": 1947, "tmdb_id": 0,      "poster_file": "Doggone_Cats_1947_poster.jpg",                   "backdrop_file": "Doggone_Cats_1947_backdrop.jpg"},
    {"title": "Scaredy Cat",                    "year": 1948, "tmdb_id": 0,      "poster_file": "Scaredy_Cat_1948_poster.jpg",                    "backdrop_file": "Scaredy_Cat_1948_backdrop.jpg"},
    {"title": "Paying the Piper",               "year": 1949, "tmdb_id": 0,      "poster_file": "Paying_the_Piper_1949_poster.jpg",               "backdrop_file": "Paying_the_Piper_1949_backdrop.jpg"},
    {"title": "Leghorn Swoggled",               "year": 1951, "tmdb_id": 0,      "poster_file": "Leghorn_Swoggled_1951_poster.jpg",               "backdrop_file": "Leghorn_Swoggled_1951_backdrop.jpg"},
    {"title": "The Prize Pest",                 "year": 1951, "tmdb_id": 0,      "poster_file": "The_Prize_Pest_1951_poster.jpg",                 "backdrop_file": "The_Prize_Pest_1951_backdrop.jpg"},
    {"title": "Cracked Quack",                  "year": 1952, "tmdb_id": 0,      "poster_file": "Cracked_Quack_1952_poster.jpg",                  "backdrop_file": "Cracked_Quack_1952_backdrop.jpg"},
    {"title": "Going Going Gosh",               "year": 1952, "tmdb_id": 0,      "poster_file": "Going_Going_Gosh_1952_poster.jpg",               "backdrop_file": "Going_Going_Gosh_1952_backdrop.jpg"},
    {"title": "Hoppy Go Lucky",                 "year": 1952, "tmdb_id": 0,      "poster_file": "Hoppy-Go-Lucky_1952_poster.jpg",                 "backdrop_file": "Hoppy-Go-Lucky_1952_backdrop.jpg"},
    {"title": "Kiddin the Kitten",              "year": 1952, "tmdb_id": 0,      "poster_file": "Kiddin_the_Kitten_1952_poster.jpg",              "backdrop_file": "Kiddin_the_Kitten_1952_backdrop.jpg"},
    {"title": "Kiss Me Cat",                    "year": 1953, "tmdb_id": 0,      "poster_file": "Kiss_Me_Cat_1953_poster.jpg",                    "backdrop_file": "Kiss_Me_Cat_1953_backdrop.jpg"},
    {"title": "The Egg-Cited Rooster",          "year": 1955, "tmdb_id": 204020, "poster_file": "The_Egg-Cited_Rooster_1955_poster.jpg",          "backdrop_file": "The_Egg-Cited_Rooster_1955_backdrop.jpg"},
    {"title": "Tweet and Sour",                 "year": 1956, "tmdb_id": 0,      "poster_file": "Tweet_and_Sour_1956_poster.jpg",                 "backdrop_file": "Tweet_and_Sour_1956_backdrop.jpg"},
    {"title": "Goldimouse and the Three Cats",  "year": 1960, "tmdb_id": 0,      "poster_file": "Goldimouse_and_the_Three_Cats_1960_poster.jpg",  "backdrop_file": "Goldimouse_and_the_Three_Cats_1960_backdrop.jpg"},
    {"title": "D Fightin Ones",                 "year": 1961, "tmdb_id": 0,      "poster_file": "D_Fightin_Ones_1961_poster.jpg",                 "backdrop_file": "D_Fightin_Ones_1961_backdrop.jpg"},
    {"title": "Good Noose",                     "year": 1962, "tmdb_id": 0,      "poster_file": "Good_Noose_1962_poster.jpg",                     "backdrop_file": "Good_Noose_1962_backdrop.jpg"},
    {"title": "Freudy Cat",                     "year": 1964, "tmdb_id": 0,      "poster_file": "Freudy_Cat_1964_poster.jpg",                     "backdrop_file": "Freudy_Cat_1964_backdrop.jpg"},
]

def fetch_by_id(tmdb_id):
    url = TMDB_MOVIE + "/" + str(tmdb_id) + "?api_key=" + TMDB_KEY
    req = urllib.request.Request(url, headers={"User-Agent": "GVV/1.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

def search_tmdb(title, year):
    params = urllib.parse.urlencode({"api_key": TMDB_KEY, "query": title, "year": year})
    url = TMDB_SEARCH + "?" + params
    req = urllib.request.Request(url, headers={"User-Agent": "GVV/1.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        results = json.loads(r.read()).get("results", [])
    if results:
        return results[0]
    params2 = urllib.parse.urlencode({"api_key": TMDB_KEY, "query": title})
    url2 = TMDB_SEARCH + "?" + params2
    req2 = urllib.request.Request(url2, headers={"User-Agent": "GVV/1.0"})
    with urllib.request.urlopen(req2, timeout=10) as r2:
        results2 = json.loads(r2.read()).get("results", [])
    return results2[0] if results2 else None

def download_img(url, dest):
    if os.path.exists(dest):
        print("    already exists, skipping")
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GVV/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            with open(dest, "wb") as f:
                f.write(r.read())
        print("    saved.")
        return True
    except Exception as e:
        print("    FAILED: " + str(e))
        return False

print("Downloading images for " + str(len(new_cartoons)) + " cartoons...\n")

for c in new_cartoons:
    print(c["title"] + " (" + str(c["year"]) + ")")
    try:
        if c["tmdb_id"]:
            result = fetch_by_id(c["tmdb_id"])
        else:
            result = search_tmdb(c["title"], c["year"])

        if not result:
            print("  NO TMDB MATCH - skipping")
            continue

        release_year = (result.get("release_date") or "")[:4]
        print("  TMDB id=" + str(result.get("id")) + " title=" + str(result.get("title")) + " (" + release_year + ")")

        poster_path   = result.get("poster_path")
        backdrop_path = result.get("backdrop_path")

        if poster_path:
            dest = "images/posters/" + c["poster_file"]
            print("  poster -> " + dest)
            download_img(TMDB_IMG_W500 + poster_path, dest)
        else:
            print("  no poster on TMDB")

        if backdrop_path:
            dest = "images/backdrops/" + c["backdrop_file"]
            print("  backdrop -> " + dest)
            download_img(TMDB_IMG_W1280 + backdrop_path, dest)
        else:
            print("  no backdrop on TMDB")

    except Exception as e:
        print("  ERROR: " + str(e))

    time.sleep(0.3)

print("\nDone.")
