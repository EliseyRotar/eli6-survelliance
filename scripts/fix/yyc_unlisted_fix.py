# -*- coding: utf-8 -*-
"""Session 48b: fix the 4 unlisted Calgary rows from image-overlay evidence.

Overlay names (read from live frames):
- loc159: 4 Ave & 2 St SW          overlay Jul 05 11:20 -> frozen
- loc169: 9 Ave & 9 St SW          overlay Jan 08 09:03 -> frozen
- loc210: 96 Ave/Airport Tr & 60 St NE  overlay Jul 21 12:51 -> frozen
- loc223: 50 Ave & Macleod Tr S    overlay Oct 19 09:33 -> live (md5 changed @95s)
Geocode each intersection via Nominatim.
"""
import csv
import json
import os
import subprocess
import time
import urllib.parse

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
CSV = os.path.join(ROOT, "controllable_Webcams.csv")
STATE = os.path.join(ROOT, "camera_testing", "yyc_fix_state.json")
LOCK = CSV + ".lock"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
DATE = "2026-10-19"

FIX = {
    "loc159": {"name": "4 Avenue / 2 Street SW (SW)", "query": "4 Avenue & 2 Street SW, Calgary, Alberta",
               "live": False, "overlay": "Jul 05 11:20"},
    "loc169": {"name": "9 Avenue / 9 Street SW (SW)", "query": "9 Avenue & 9 Street SW, Calgary, Alberta",
               "live": False, "overlay": "Jan 08 09:03"},
    "loc210": {"name": "96 Avenue / Airport Trail & 60 Street NE (NE)",
               "query": "96 Avenue & Airport Trail & 60 Street NE, Calgary, Alberta",
               "live": False, "overlay": "Jul 21 12:51"},
    "loc223": {"name": "50 Avenue / Macleod Trail S (S)", "query": "50 Avenue & Macleod Trail S, Calgary, Alberta",
               "live": True, "overlay": "Oct 19 09:33"},
}


def nominatim(q):
    url = "https://nominatim.openstreetmap.org/search?format=json&limit=1&q=" + urllib.parse.quote(q)
    p = subprocess.run(["curl", "-sL", "-A", UA + " eli6-surveillance/1.0", "--max-time", "25", url],
                       capture_output=True, text=True, timeout=35)
    try:
        d = json.loads(p.stdout)
        if d:
            return d[0]["lat"], d[0]["lon"], d[0].get("type", ""), d[0].get("display_name", "")[:80]
    except Exception:
        pass
    return None, None, "", ""


if os.path.exists(LOCK):
    raise SystemExit("lock exists")
os.close(os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
try:
    geo = {}
    for loc, f in FIX.items():
        lat, lon, typ, dn = nominatim(f["query"])
        geo[loc] = (lat, lon, typ, dn)
        print("geo %-7s -> %s %s (%s) %s" % (loc, lat, lon, typ, dn))
        time.sleep(1.2)

    with open(CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    updated = 0
    for r in rows:
        combo = (r.get("live_stream_url") or "") + (r.get("url") or "")
        for loc, f in FIX.items():
            if "trafficcam.calgary.ca/%s.jpg" % loc in combo and (r.get("csv_id") or "").startswith("yyc_"):
                r["project_name"] = f["name"]
                r["description"] = "City of Calgary traffic camera %s (unlisted on open data k7p9-kppz)" % f["name"]
                r["live_status"] = "live" if f["live"] else ""
                lat, lon, typ, dn = geo[loc]
                if lat:
                    r["lat"], r["lon"] = str(lat), str(lon)
                    r["location_precision"] = "precise"
                    r["geo_source"] = "nominatim-poi"
                notes = r.get("notes") or ""
                add = ("overlay-name+timestamp='%s'; frozen-md5-unchanged@95s-%s; "
                       "geocoded-nominatim@%s" % (f["overlay"], DATE, DATE)) if not f["live"] else \
                      ("overlay-name+timestamp='%s'; live-md5-changed@95s-%s; "
                       "geocoded-nominatim@%s" % (f["overlay"], DATE, DATE))
                r["notes"] = (notes + "; " + add) if notes else add
                updated += 1
                print("  updated %s %s live=%s" % (r["csv_id"], f["name"], f["live"]))

    tmp = CSV + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, CSV)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump({"date": DATE, "phase": "done", "updated": updated}, f)
    print("[yyc-fix] updated=%d total=%d" % (updated, len(rows)))
finally:
    try:
        os.remove(LOCK)
    except OSError:
        pass
