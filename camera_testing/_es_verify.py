# -*- coding: utf-8 -*-
"""Verify Session 47 CSV changes."""
import csv
from collections import Counter

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
csv.field_size_limit(10**7)
rect_by_pref = Counter()
rect_tv = []
dead = []
new_rows = []
maxidx = 0
n = 0
with open(ROOT + r"\controllable_Webcams.csv", encoding="utf-8", newline="") as f:
    rd = csv.DictReader(f)
    for r in rd:
        n += 1
        try:
            if int(r["idx"]) > maxidx:
                maxidx = int(r["idx"])
        except ValueError:
            pass
        if "rectified-20261017" in (r["notes"] or ""):
            p = r["csv_id"].split("_")[0]
            rect_by_pref[p] += 1
            if p in ("tv", "web") and len(rect_tv) < 12:
                rect_tv.append((r["csv_id"], r["project_name"][:55], r["country"],
                                r["region"][:28], r["lat"], r["lon"], r["category"]))
        if "image-404@2026-10-17" in (r["notes"] or ""):
            dead.append((r["csv_id"], r["http_status"], r["live_status"], r["project_name"][:30]))
        try:
            if int(r["idx"]) >= 240220:
                new_rows.append(r)
        except ValueError:
            pass

print("rows:", n, "| max idx:", maxidx)
print("rectified by prefix:", dict(rect_by_pref))
print("rectified tv/web samples:")
for t in rect_tv:
    print("   ", t)
print("dead-marked:", len(dead))
for d in dead[:25]:
    print("   ", d)

print("\nnew rows:", len(new_rows))
print("new prefixes:", dict(Counter(r["csv_id"].split("_")[0] for r in new_rows)))
print("new live_status:", dict(Counter(r["live_status"] for r in new_rows)))
print("new http_status:", dict(Counter(r["http_status"] for r in new_rows)))
print("new visibility:", dict(Counter(r["visibility"] for r in new_rows)))
print("new category:", dict(Counter(r["category"] for r in new_rows)))
for r in new_rows[:3] + new_rows[-3:]:
    print("  ", r["csv_id"], "|", r["project_name"][:50], "|", r["live_stream_url"][:75])
    print("     lat:", r["lat"], "lon:", r["lon"], "| cty:", r["country"], "| reg:", r["region"][:25],
          "| ls:", r["live_status"], "| http:", r["http_status"], "| cat:", r["category"])
# sanity on rectified spot values
bad = []
with open(ROOT + r"\controllable_Webcams.csv", encoding="utf-8", newline="") as f:
    for r in csv.DictReader(f):
        if "rectified-20261017" not in (r["notes"] or ""):
            continue
        try:
            lat, lon = float(r["lat"]), float(r["lon"])
        except Exception:
            continue
        if not (-10.5 <= lon <= 5.0 and 34.5 <= lat <= 44.5):
            bad.append((r["csv_id"], r["project_name"][:40], r["country"], lat, lon))
print("\nrectified rows with coords outside Spain/Andorra bbox:", len(bad))
for b in bad[:10]:
    print("   ", b)
