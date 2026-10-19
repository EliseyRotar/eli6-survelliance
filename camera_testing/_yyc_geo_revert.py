# -*- coding: utf-8 -*-
"""Session 48b: revert 3 bad city-centroid geocodes (169/210/223) to no-coords."""
import csv
import os

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
CSV = os.path.join(ROOT, "controllable_Webcams.csv")
LOCK = CSV + ".lock"
BAD = {"loc169", "loc210", "loc223"}

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
        if not (r.get("csv_id") or "").startswith("yyc_"):
            continue
        for loc in BAD:
            if "trafficcam.calgary.ca/%s.jpg" % loc in combo:
                r["lat"] = ""
                r["lon"] = ""
                r["location_precision"] = "no_geocode_result"
                r["geo_source"] = ""
                notes = (r.get("notes") or "")
                add = "nominatim-city-centroid-rejected@2026-10-19"
                if add not in notes:
                    r["notes"] = (notes + "; " + add) if notes else add
                upd += 1
                print("reverted", r["csv_id"], loc)
    tmp = CSV + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, CSV)
    print("[yyc-geo-revert] updated=%d" % upd)
finally:
    try:
        os.remove(LOCK)
    except OSError:
        pass
