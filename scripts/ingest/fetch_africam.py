#!/usr/bin/env python3
"""Fetch all Africam lodge pages, extract data-vid, verify via oEmbed."""
import urllib.request
import urllib.error
import json
import re
import ssl
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# All 35 lodges (we'll skip the 9 Kenya ones already done)
LODGES = [
    # (slug, name, country, region, lat, lng)
    ("serengeti", "Elewana Serengeti Explorer", "Tanzania", "Serengeti", -2.333, 34.834),
    ("onguma-the-fort-live-stream-africam-live-camera-bordering-etosha-namibia", "Onguma - The Fort", "Namibia", "Etosha", -19.0, 15.917),
    ("safarihoek", "Safarihoek", "Namibia", "Etosha Heights", -19.5, 15.833),
    ("deteemasprings", "Deteema Springs", "Zimbabwe", "Hwange", -19.0, 26.5),
    ("the-hide", "The Hide", "Zimbabwe", "Hwange", -19.0, 26.5),
    ("linkwasha", "Wilderness Linkwasha", "Zimbabwe", "Hwange", -19.0, 26.5),
    ("hwange-safari-lodge", "Hwange Safari Lodge", "Zimbabwe", "Hwange", -19.0, 26.5),
    ("tembo-plains", "Tembo Plains", "Zimbabwe", "Sapi Private Reserve", -15.85, 29.95),
    ("victoria-falls-safari-lodge", "Victoria Falls Safari Lodge", "Zimbabwe", "Victoria Falls", -17.925, 25.857),
    ("senyati", "Senyati Safari Camp", "Botswana", "Chobe", -18.5, 24.0),
    ("kalahari", "Kalahari Salt Pan", "Botswana", "Makgadikgadi Pans", -20.5, 25.5),
    ("twin-pan", "Twin Pan - Zarafa Camp", "Botswana", "Selinda Reserve", -19.0, 23.5),
    ("thebasin-selinda", "The Basin - Selinda Camp", "Botswana", "Selinda Reserve", -19.0, 23.5),
    ("jackscamp", "Jack's Camp", "Botswana", "Makgadikgadi Pans", -20.5, 25.5),
    ("meno", "Meno a Kwena", "Botswana", "Boteti River", -19.0, 23.5),
    ("camelthorn", "Camelthorn", "Botswana", "Boteti River", -19.0, 23.5),
    ("moela", "Moela Lodge", "Botswana", "Boteti River", -19.0, 23.5),
    ("elephant-pan", "Elephant Pan", "Botswana", "Khwai Private Reserve", -19.0, 23.5),
    ("ulusaba", "Ulusaba", "South Africa", "Sabi Sand", -24.766, 31.5),
    ("black-eagle", "Black Eagle Nest", "South Africa", "Selati Game Reserve", -23.5, 30.0),
    ("hesc", "HESC", "South Africa", "Hoedspruit", -24.35, 30.95),
    ("penguins", "Penguins", "South Africa", "Stony Point", -34.367, 18.883),
    ("lesser-flamingos", "Lesser Flamingos", "South Africa", "Kamfers Dam", -29.667, 18.5),
    ("serondella", "Serondella", "South Africa", "Thornybush Game Reserve", -24.5, 31.2),
    ("kingscamp", "Kings Camp", "South Africa", "Timbavati Game Reserve", -24.0, 31.25),
    ("naledi-bush-lodge", "Naledi Bush Lodge", "South Africa", "Olifants West", -24.0, 31.25),
    ("nkorho-bush-lodge", "Nkorho Bush Lodge", "South Africa", "Sabi Sand", -24.766, 31.5),
    ("silvan-safari", "Silvan Safari", "South Africa", "Sabi Sand", -24.766, 31.5),
    ("simbavati-waterside", "Simbavati Waterside", "South Africa", "Klaserie", -24.0, 31.25),
    ("tembe-elephant-park", "Tembe Elephant Park", "South Africa", "Maputaland", -27.0, 32.5),
    ("tau-game-lodge", "Tau Game Lodge", "South Africa", "Madikwe", -24.75, 26.4),
    ("kwa-maritane", "Kwa Maritane Bush Lodge", "South Africa", "Pilanesberg", -25.25, 27.083),
    ("kruger-shalati", "Kruger Shalati", "South Africa", "Kruger National Park", -25.0, 31.5),
    ("jabulani-safari-lodge", "Jabulani Safari Lodge", "South Africa", "Kapama", -24.45, 31.0),
    ("founders-lodge-by-mantis", "Founders Lodge", "South Africa", "Eastern Cape", -33.5, 26.5),
]

# 9 already-done Kenya slugs (skip these — but we list so we can ensure full set)
KENYA_DONE = {
    "angama-amboseli": ("Angama Amboseli", "Amboseli", "XsOU8JnEpNM"),
    "porini": ("Porini Rhino Camp", "Ol Pejeta", "5dhmXmUD1ZE"),
    "angamamara": ("Angama Mara", "Maasai Mara", "Njur5IV7icE"),
    "marariver": ("Mara River Fig Tree", "Mara Triangle", "ACc7IkdOF-Y"),
    "marariver-main": ("Mara River Main Crossing", "Mara Triangle", "BaEFc79IMCA"),
    "tortilis": ("Tortilis Camp", "Amboseli", "XyPU5-pNg5E"),
    "mahali-mzuri-waterhole": ("Mahali Mzuri Waterhole", "Maasai Mara", "ZWhvO6R37ck"),
    "mahali-mzuri-landscape": ("Mahali Mzuri Landscape", "Maasai Mara", "jIh2FYqMOw0"),
    "finch-hattons": ("Finch Hattons", "Tsavo West", "Xe9CPAdyAro"),
    "ol-donyo-lodge": ("ol Donyo Lodge", "Chyulu Hills", "XsOU8JnEpNM"),
    "lentorre-lodge": ("Lentorre Lodge", "Rift Valley", "bEmFpjwMOvs"),
}

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        return f"ERROR: {e}"

def get_page(slug):
    url = f"https://africam.com/lodge/{slug}/"
    return slug, fetch(url)

def extract_vids(html):
    """Find all data-vid attributes in play_vid_pop contexts.
    Distinguish: live stream player (main) vs. CTA (intro/promo/about).
    Strategy: scan all data-vid; the one associated with the live player block
    is typically a direct child of .play_vid_pop with no .cta_block, or the
    one inside the iframe wrapper. We return ALL vids and let the verifier
    rank them by checking oEmbed title."""
    if not html or html.startswith("ERROR"):
        return []
    # Find all data-vid attrs on play_vid_pop elements
    pattern = re.compile(r'class="[^"]*play_vid_pop[^"]*"[^>]*data-vid="([^"]+)"', re.IGNORECASE)
    pattern2 = re.compile(r'data-vid="([^"]+)"[^>]*class="[^"]*play_vid_pop', re.IGNORECASE)
    vids = set()
    for m in pattern.finditer(html):
        vids.add(m.group(1))
    for m in pattern2.finditer(html):
        vids.add(m.group(1))
    # Also find any data-vid at all in a broad scan
    pattern3 = re.compile(r'data-vid="([^"]{6,20})"')
    for m in pattern3.finditer(html):
        v = m.group(1)
        if 8 <= len(v) <= 15:  # YT ids are 11 chars
            vids.add(v)
    return list(vids)

def oembed(yt_id):
    url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={yt_id}&format=json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            data = json.loads(r.read())
        return data.get("title", "")
    except urllib.error.HTTPError as e:
        return f"HTTP{e.code}"
    except Exception as e:
        return f"ERR:{e}"

def main():
    results = []
    print(f"Fetching {len(LODGES)} lodge pages in parallel...", file=sys.stderr)
    
    # First fetch all pages
    pages = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(get_page, slug): slug for slug, *_ in LODGES}
        for fut in as_completed(futs):
            slug, html = fut.result()
            pages[slug] = html
    
    # Then extract vids
    candidates = {}  # slug -> [vids]
    for slug, *_ in LODGES:
        vids = extract_vids(pages.get(slug, ""))
        candidates[slug] = vids
    
    # Verify via oEmbed
    print("Verifying via oEmbed...", file=sys.stderr)
    verified = {}  # (slug, vid) -> title
    verif_futs = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        for slug, vids in candidates.items():
            for v in vids:
                verif_futs[ex.submit(oembed, v)] = (slug, v)
        for fut in as_completed(verif_futs):
            slug, v = verif_futs[fut]
            title = fut.result()
            verified[(slug, v)] = title
    
    # Build output
    for slug, name, country, region, lat, lng in LODGES:
        vids = candidates.get(slug, [])
        # Prefer "live" titles over intro/promo
        live_vid = None
        live_title = None
        all_vids_info = []
        for v in vids:
            t = verified.get((slug, v), "?")
            all_vids_info.append({"vid": v, "title": t})
            if live_vid is None:
                # heuristics: title contains "live", "africa", "wild", "stream" or no "about"/"intro"/"promo"
                tlow = t.lower() if isinstance(t, str) else ""
                if tlow and "about" not in tlow and "intro" not in tlow and "promo" not in tlow and "lodge tour" not in tlow and "welcome" not in tlow:
                    live_vid = v
                    live_title = t
        if not live_vid and vids:
            live_vid = vids[0]
            live_title = verified.get((slug, vids[0]), "")
        results.append({
            "lodge_slug": slug,
            "name": name,
            "yt_id": live_vid,
            "yt_title": live_title,
            "country": country,
            "region": region,
            "lat": lat,
            "lng": lng,
            "all_candidates": all_vids_info,
        })
    
    # Write results
    with open("C:/Users/eli6-admin/Documents/eli6-surveillance/data/africam_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print(f"\n=== SUMMARY ===")
    for r in results:
        ok = "OK" if r["yt_id"] else "MISSING"
        print(f"[{ok}] {r['name']:<35} {r['yt_id'] or '-':<12} | {r['yt_title'] or '-'}")
        if r["all_candidates"]:
            for c in r["all_candidates"]:
                print(f"        alt: {c['vid']} -> {c['title']}")

if __name__ == "__main__":
    main()
