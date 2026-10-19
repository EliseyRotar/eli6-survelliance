# -*- coding: utf-8 -*-
"""Session 48b: retry geocode for loc169/210/223 with simpler queries."""
import csv
import json
import os
import subprocess
import time
import urllib.parse

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
CSV = os.path.join(ROOT, "controllable_Webcams.csv")
LOCK = CSV + ".lock"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) eli6-surveillance/1.0"

TRIES = {
    "loc169": ["9 Ave SW & 9 St SW, Calgary",
               "9 Street West & 9 Avenue West, Calgary",
               "900 9 St SW, Calgary, Alberta"],
    "loc210": ["96 Ave NE & 60 St NE, Calgary",
               "Airport Trail NE & 60 Street NE, Calgary",
               "60 Street Northeast & Northeast 96 Avenue, Calgary"],
    "loc223": ["Macleod Trail S & 50 Ave SE, Calgary",
               "Macleod Trail SE & 50 Avenue SE, Calgary",
               "50 Avenue Southeast & Macleod Trail Southeast, Calgary",
               "Macleod Trail & 50 Ave, Calgary, Alberta"],
}


def nominatim(q):
    url = "https://nominatim.openstreetmap.org/search?format=json&limit=1&q=" + urllib.parse.quote(q)
    p = subprocess.run(["curl", "-sL", "-A", UA, "--max-time", "25", url],
                       capture_output=True, text=True, timeout=35)
    try:
        d = json.loads(p.stdout)
        if d:
            return d[0]["lat"], d[0]["lon"], d[0].get("type", ""), d[0].get("display_name", "")[:90]
    except Exception:
        pass
    return None, None, "", ""


found = {}
for loc, qs in TRIES.items():
    for q in qs:
        lat, lon, typ, dn = nominatim(q)
        print("%-7s %-48s -> %s %s (%s)" % (loc, q[:48], lat, lon, typ))
        if lat:
            found[loc] = (lat, lon, typ, dn)
            break
        time.sleep(1.3)

if not found:
    print("nothing found")
    raise SystemExit(0)

if os.path.exists(LOCK):
    raise SystemExit("lock exists")
os.close(os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
try:
    with open(CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    upd = 0
    for r in rows:
        combo = (r.get("live_stream_url") or "") + (r.get("url") or "")
        for loc, (lat, lon, typ, dn) in found.items():
            if "trafficcam.calgary.ca/%s.jpg" % loc in combo and (r.get("csv_id") or "").startswith("yyc_"):
                r["lat"], r["lon"] = str(lat), str(lon)
                r["location_precision"] = "precise"
                r["geo_source"] = "nominatim-poi"
                notes = r.get("notes") or ""
                add = "geocoded-nominatim-retry@2026-10-19 (%s)" % typ
                r["notes"] = (notes + "; " + add) if notes else add
                upd += 1
                print("  geo-updated", r["csv_id"], loc, lat, lon)
    tmp = CSV + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, CSV)
    print("[yyc-geo-retry] updated=%d" % upd)
finally:
    try:
        os.remove(LOCK)
    except OSError:
        pass
