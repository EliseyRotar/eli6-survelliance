# -*- coding: utf-8 -*-
"""Existing DGT rows inspection."""
import csv
from collections import Counter

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
csv.field_size_limit(10**7)
rows = []
pref = Counter()
with open(ROOT + r"\controllable_Webcams.csv", encoding="utf-8", newline="") as f:
    for r in csv.DictReader(f):
        u = (r.get("live_stream_url") or "") + " " + (r.get("url") or "") + " " + (r.get("geo_source") or "") + " " + (r.get("host") or "")
        if "dgt.es" in u or "etraffic" in u or "infocar" in u:
            rows.append(r)
            cid = r.get("csv_id") or ""
            pref[cid.split("_")[0]] += 1
print("dgt-related rows:", len(rows))
print("prefixes:", dict(pref))
for r in rows[:8]:
    print(" idx", r["idx"], "|", r["csv_id"], "|", r["project_name"][:70])
    print("   url:", r["url"][:90])
    print("   stream:", r["live_stream_url"][:110])
    print("   type:", r["type"], "| cat:", r["category"], "| country:", r["country"], "| geo:", r["geo_source"], "| lat:", r["lat"], "lon:", r["lon"])
    print("   notes:", (r["notes"] or "")[:200])
# id span
idxs = [int(r["idx"]) for r in rows if r["idx"].isdigit()]
print("idx span:", (min(idxs), max(ids)) if idxs else None)
# sample of distinct live_stream_url patterns
pats = Counter()
for r in rows:
    u = r["live_stream_url"]
    if "camarasEtraffic" in u:
        pats["camarasEtraffic"] += 1
    elif "data/camaras" in u:
        pats["data/camaras"] += 1
    else:
        pats[u[:60]] += 1
print("patterns:", dict(pats.most_common(10)))
