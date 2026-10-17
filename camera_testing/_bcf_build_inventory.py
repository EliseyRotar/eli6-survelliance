# -*- coding: utf-8 -*-
"""Assemble BC Ferries cam inventory JSON from recon artifacts."""
import json
import re
import os

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"

TERMINALS = {
    "ALF": "Moresby Island (Alliford Bay)",
    "ALR": "Cormorant Island (Alert Bay)",
    "BEC": "Bella Coola",
    "BKY": "Buckley Bay",
    "BOW": "Bowen Island (Snug Cove)",
    "BTW": "Brentwood Bay",
    "CAM": "Campbell River",
    "CHM": "Chemainus",
    "CMX": "Comox (Little River)",
    "COR": "Cortes Island (Whaletown)",
    "CFT": "Crofton",
    "DNE": "Denman Island East (Gravelly Bay)",
    "DNM": "Denman Island West",
    "DUK": "Nanaimo (Duke Point)",
    "ERL": "Sunshine Coast (Earls Cove)",
    "FUL": "Salt Spring Island (Fulford Harbour)",
    "GAB": "Gabriola Island (Descanso Bay)",
    "HER": "Quadra Island (Heriot Bay)",
    "HRN": "Hornby Island (Shingle Spit)",
    "HSB": "Vancouver (Horseshoe Bay)",
    "KPR": "Penelakut Island (Telegraph Harbour)",
    "LNG": "Sunshine Coast (Langdale)",
    "MCN": "Port McNeill",
    "MIL": "Mill Bay",
    "NAH": "Nanaimo (Nanaimo Harbour)",
    "NAN": "Nanaimo (Departure Bay)",
    "PBB": "Bella Bella (McLoughlin Bay)",
    "PLH": "Salt Spring Island (Long Harbour)",
    "POB": "Pender Island (Otter Bay)",
    "POF": "Ocean Falls",
    "PPH": "Port Hardy (Bear Cove)",
    "PPR": "Prince Rupert",
    "PSK": "Graham Island (Skidegate)",
    "PVB": "Mayne Island (Village Bay)",
    "PWR": "Powell River (Westview)",
    "QDR": "Quadra Island (Quathiaski Cove)",
    "SLT": "Powell River (Saltery Bay)",
    "STB": "Galiano Island (Sturdies Bay)",
    "SWB": "Victoria (Swartz Bay)",
    "TEX": "Texada Island (Blubber Bay)",
    "THT": "Thetis Island (Preedy Harbour)",
    "TSA": "Vancouver (Tsawwassen)",
    "VES": "Salt Spring Island (Vesuvius Bay)",
}

with open(ROOT + r"\_bcf_geocode.json", encoding="utf-8") as f:
    GEO = json.load(f)
GEO["PBB"] = {
    "lat": 52.1388229,
    "lon": -128.1437584,
    "display": "Bella Bella (McLoughlin Bay), McLouchlin Bay Ferry Terminal, Area A (Ocean Falls)",
}

with open(ROOT + r"\_bcf_recon2.json", encoding="utf-8") as f:
    recon2 = json.load(f)
cam_meta = recon2["cam_meta"]

with open(ROOT + r"\_bcf_cams_probe.json", encoding="utf-8") as f:
    probe = json.load(f)

# dedupe case-insensitive, prefer uppercase filename
by_lower = {}
for h in probe["hits"]:
    url = h["url"]
    if not url.lower().endswith(".jpg"):
        continue
    key = url.lower()
    prev = by_lower.get(key)
    if prev is None or (prev != url and url == url.upper().replace("CAM", "cam")):
        pass
    # prefer the all-uppercase CODE form
    if prev is None or ("/cam" in url and url.split("/")[-1] == url.split("/")[-1].upper()) or "/cam" not in url:
        by_lower[key] = url

# normalize: pick canonical filename camN_CODE.jpg with CODE uppercase except keep working URL
cams = []
for key, url in sorted(by_lower.items()):
    fn = url.rsplit("/", 1)[-1]
    m = re.match(r"cam(\d)_([A-Za-z]{3})\.jpg$", fn)
    if not m:
        continue
    n, code_raw = m.group(1), m.group(2)
    code = code_raw.upper()
    if code not in TERMINALS:
        print("UNKNOWN CODE", code, url)
        continue
    meta = cam_meta.get(url) or cam_meta.get(
        "https://ccimg.bcferries.com/cc/support/terminals/" + fn
    ) or {}
    # also try lowercase key from recon (cam2_erl)
    if not meta:
        for k, v in cam_meta.items():
            if k.lower().endswith("/" + fn.lower()):
                meta = v
                break
    captions = meta.get("captions") or []
    # cam1 default caption
    if n == "1" and not captions:
        captions = ["Traffic at the terminal"]
    geo = GEO.get(code, {})
    cams.append({
        "cam_n": int(n),
        "code": code,
        "file": f"cam{n}_{code}.jpg",
        "url": f"https://ccimg.bcferries.com/cc/support/terminals/cam{n}_{code}.jpg",
        "terminal": TERMINALS[code],
        "captions": captions,
        "unlinked": not meta,
        "lat": geo.get("lat"),
        "lon": geo.get("lon"),
        "geo_display": geo.get("display"),
    })

print("cams:", len(cams))
from collections import Counter
print("per terminal:", Counter(c["code"] for c in cams).most_common())
print("unlinked:", [c["file"] for c in cams if c["unlinked"]])
missing_geo = sorted({c["code"] for c in cams if c["lat"] is None})
print("missing geo:", missing_geo)

with open(ROOT + r"\_bcf_cams_inventory.json", "w", encoding="utf-8") as f:
    json.dump(cams, f, indent=2)
print("saved inventory")
