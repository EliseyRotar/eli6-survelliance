#!/usr/bin/env python3
"""V2: Better extraction - find the actual LIVE stream per lodge (vs intro/highlight)."""
import urllib.request
import urllib.error
import json
import re
import ssl
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

LODGES = [
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
    """Find all data-vid attrs and which one is the LIVE stream player."""
    if not html or html.startswith("ERROR"):
        return [], None
    # The pattern: <a class="cta_block play_vid_pop show_vid_play" data-vid="...">About Lodge</a>
    #              <a class="cta_block play_vid_pop show_vid_play" data-vid="...">About Africam camera & live stream</a>
    # The iframe live player is loaded dynamically. But the "About Africam camera & live stream" button
    # actually pops up a video player showing the same content as the embedded live stream.
    # There's also a div with class "image play_vid_pop" (the live cam block on the homepage, not on lodge pages)
    
    # Find all data-vid with surrounding class+title context
    # pattern: class="...play_vid_pop..." data-vid="ID" ... title text ... 
    pattern = re.compile(
        r'class="([^"]*play_vid_pop[^"]*)"[^>]*data-vid="([A-Za-z0-9_-]{6,15})"[^>]*>(.*?)(?=</a>|</div>)',
        re.IGNORECASE | re.DOTALL
    )
    results = []
    for m in pattern.finditer(html):
        cls = m.group(1)
        vid = m.group(2)
        inner = m.group(3)
        # Extract title from inner
        title_m = re.search(r'<span class="title">\s*([^<]+?)\s*</span>', inner)
        title = title_m.group(1) if title_m else ""
        results.append({"vid": vid, "class": cls, "context_title": title.strip()})
    
    # Also: <a class="image play_vid_pop" data-vid="..." (live cam block)
    # Some pages have multiple such divs (multiple cams)
    # The class contains "play_vid_pop" - find each
    return results, None

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

def is_live_stream_title(title):
    """Heuristic: live stream titles typically start with LIVE or contain 'Live Camera/Stream/Cam'."""
    if not title or not isinstance(title, str):
        return False
    t = title.lower()
    # Strong signals
    if t.startswith("live ") or t.startswith("live:"):
        return True
    if "live wildlife camera" in t or "live wildlife stream" in t:
        return True
    if "live hide cam" in t or "live from" in t or "live at" in t or "live cam" in t:
        return True
    if "live camera at" in t or "live stream at" in t or "live stream from" in t:
        return True
    if "live | " in t or "| live " in t:
        return True
    # Lodge name + Live pattern (e.g. "Kings Camp | Live Wildlife Stream")
    if "| live" in t and ("stream" in t or "cam" in t or "waterhole" in t or "wildlife" in t):
        return True
    return False

def main():
    pages = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(get_page, slug): slug for slug, *_ in LODGES}
        for fut in as_completed(futs):
            slug, html = fut.result()
            pages[slug] = html
    
    # Extract vids per page
    candidates = {}
    for slug, *_ in LODGES:
        results, _ = extract_vids(pages.get(slug, ""))
        candidates[slug] = results
    
    # Verify titles via oEmbed
    print("Verifying via oEmbed...", file=sys.stderr)
    titles = {}
    verif_futs = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        for slug, results in candidates.items():
            for r in results:
                verif_futs[ex.submit(oembed, r["vid"])] = (slug, r["vid"])
        for fut in as_completed(verif_futs):
            slug, v = verif_futs[fut]
            titles[(slug, v)] = fut.result()
    
    # Build output
    output = []
    print(f"\n=== FINAL RESULTS ===\n")
    for slug, name, country, region, lat, lng in LODGES:
        results = candidates.get(slug, [])
        enriched = []
        for r in results:
            t = titles.get((slug, r["vid"]), "?")
            enriched.append({
                "vid": r["vid"],
                "class": r["class"],
                "context_title": r["context_title"],
                "oembed_title": t,
                "is_live": is_live_stream_title(t) or is_live_stream_title(r["context_title"]),
            })
        # Primary live stream = first one with is_live=True, fall back to "About Africam camera" CTA
        live = next((e for e in enriched if e["is_live"]), None)
        if not live:
            # Fallback: the "About Africam camera & live stream" CTA - this is the same as the iframe
            ab = next((e for e in enriched if "africa" in e["context_title"].lower() and "live" in e["context_title"].lower()), None)
            live = ab or (enriched[0] if enriched else None)
        # Secondary cams: any other items that look like cam names
        secondaries = [e for e in enriched if e is not live and (
            "Live" in (e["oembed_title"] or "") or 
            "Live" in (e["context_title"] or "") or
            "CAM" in e["class"].upper() or
            "image play_vid_pop" in e["class"]
        )]
        out = {
            "lodge_slug": slug,
            "name": name,
            "yt_id": live["vid"] if live else None,
            "yt_title": live["oembed_title"] if live else None,
            "country": country,
            "region": region,
            "lat": lat,
            "lng": lng,
        }
        if secondaries:
            out["secondary_cams"] = [
                {"yt_id": s["vid"], "title": s["oembed_title"]} for s in secondaries
            ]
        output.append(out)
        ok = "OK" if out["yt_id"] else "MISSING"
        print(f"[{ok}] {name:<35} {out['yt_id'] or '-':<12} | {out['yt_title'] or '-'}")
        if secondaries:
            for s in secondaries:
                print(f"        + cam: {s['vid']} -> {s['oembed_title']}")
    
    # Write
    with open("C:/Users/eli6-admin/Documents/eli6-surveillance/africam_results.json", "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    # Also write full enriched dump for debugging
    with open("C:/Users/eli6-admin/Documents/eli6-surveillance/africam_full.json", "w") as f:
        debug = {slug: candidates.get(slug, []) for slug, *_ in LODGES}
        # Add titles
        for slug in debug:
            for r in debug[slug]:
                r["oembed_title"] = titles.get((slug, r["vid"]), "?")
                r["is_live"] = is_live_stream_title(r.get("oembed_title", "")) or is_live_stream_title(r["context_title"])
        json.dump(debug, f, indent=2, ensure_ascii=False)
    print(f"\nWrote africam_results.json (clean) and africam_full.json (debug)")

if __name__ == "__main__":
    main()
