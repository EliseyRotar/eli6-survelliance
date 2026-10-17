# -*- coding: utf-8 -*-
"""Precise inventory-vs-CSV overlap in each source's id space + row metadata quality."""
import csv
import json
import os
import re
from collections import defaultdict

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
CSV = r"C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv"
csv.field_size_limit(10**7)

inv = json.load(open(os.path.join(ROOT, "_es_inventory.json"), encoding="utf-8"))


def norm(u):
    return (u or "").replace("https://", "http://")


# CSV side: extract per-source id sets
csv_ids = defaultdict(set)   # prefix-ish -> set of ids
csv_urlset = set()           # normalized full urls for exact fallback
csv_rows = []                # (idx, csv_id, project_name, country, region, city, road, lat, lon, geo, notes, url, stream)
with open(CSV, encoding="utf-8", newline="") as f:
    for r in csv.DictReader(f):
        u = norm((r.get("live_stream_url") or "")) + " " + norm((r.get("url") or ""))
        for part in (r.get("live_stream_url") or "", r.get("url") or ""):
            if part:
                csv_urlset.add(norm(part))
        u = norm((r.get("live_stream_url") or "")) + " " + norm((r.get("url") or ""))
        e = None
        if "/static/files/tr/camaras/" in u:
            e = "eusk"
            m = re.findall(r"trafikoa[\w.-]*/static/files/tr/camaras/(\d+)\.jpg", u)
            for x in m:
                csv_ids["eusk"].add(x)
        if "mct.gencat.cat/mct2bo" in u or "sctidcam=" in u or "TransitCamera?nom=" in u:
            e = "cat"
            m = re.findall(r"sctidcam=([\w.-]+?)(?:\.gif|\.jpg)?(?:&|\s|$)", u)
            m += re.findall(r"TransitCamera\?nom=([\w.-]+?)(?:\.gif|\.jpg)?(?:&|\s|$)", u)
            for x in m:
                csv_ids["cat"].add(x.rstrip("."))
        if "imgs.mobilitat.ad/prod/" in u:
            e = "ando"
            m = re.findall(r"imgs\.mobilitat\.ad/prod/([\w.-]+)\.gif", u)
            for x in m:
                csv_ids["ando"].add(x)
        if "vitoria-gasteiz.org/c11-01w/cameras" in u:
            e = "vit"
            m = re.findall(r"id=([\w_]+)", u)
            for x in m:
                csv_ids["vit"].add(x)
        if "youtube.com/watch?v=" in u:
            e = "web"
            for x in re.findall(r"watch\?v=([\w-]+)", u):
                csv_ids["web"].add(x)
        if e:
            csv_rows.append({"pfx": e, "idx": r["idx"], "csv_id": r["csv_id"],
                             "name": r["project_name"], "country": r["country"],
                             "region": r["region"], "city": r["city"], "road": r["road"],
                             "lat": r["lat"], "lon": r["lon"], "geo": r["geo_source"],
                             "notes": r["notes"][:150], "url": r["url"][:110],
                             "stream": (r["live_stream_url"] or "")[:110], "_raw": r})

# inventory id sets
inv_ids = defaultdict(set)
for e in inv:
    u = e["image_url"]
    if e["prefix"] == "eusk":
        m = re.search(r"camaras/(\d+)\.jpg", u)
        if m:
            inv_ids["eusk"].add(m.group(1))
    elif e["prefix"] == "cat":
        m = re.search(r"sctidcam=([\w.-]+?)(?:\.gif|\.jpg)?$", u)
        if m:
            inv_ids["cat"].add(m.group(1).rstrip("."))
        else:
            inv_ids["cat"].add(e["key"])
    elif e["prefix"] == "ando":
        m = re.search(r"prod/([\w.-]+)\.gif", u)
        if m:
            inv_ids["ando"].add(m.group(1))
    elif e["prefix"] == "vit":
        m = re.search(r"id=([\w_]+)", u)
        if m:
            inv_ids["vit"].add(m.group(1))
    elif e["prefix"] == "web":
        m = re.search(r"watch\?v=([\w-]+)", e.get("stream_url", ""))
        if m:
            inv_ids["web"].add(m.group(1))

print("== id-space overlap ==")
exclude_keys = set()
for pfx in ["eusk", "cat", "ando", "vit", "web", "cnt"]:
    a, b = inv_ids.get(pfx, set()), csv_ids.get(pfx, set())
    inter = a & b
    only_inv = a - b
    print(f"{pfx}: inv={len(a)} csv={len(b)} overlap={len(inter)} NEW={len(only_inv)}")
    if only_inv and pfx in ("eusk", "cat", "ando", "vit", "web"):
        print("   new ids:", sorted(only_inv)[:20])

# map exclude keys
def inv_id(e):
    u = e["image_url"]
    if e["prefix"] == "eusk":
        m = re.search(r"camaras/(\d+)\.jpg", u)
        return m.group(1) if m else None
    if e["prefix"] == "cat":
        m = re.search(r"sctidcam=([\w.-]+?)(?:\.gif|\.jpg)?$", u)
        if not m:
            return None
        return m.group(1).rstrip(".")
    if e["prefix"] == "ando":
        m = re.search(r"prod/([\w.-]+)\.gif", u)
        return m.group(1) if m else None
    if e["prefix"] == "vit":
        m = re.search(r"id=([\w_]+)", u)
        return m.group(1) if m else None
    if e["prefix"] == "web":
        m = re.search(r"watch\?v=([\w-]+)", e.get("stream_url", ""))
        return m.group(1) if m else None
    return None


for e in inv:
    iid = inv_id(e)
    if iid and iid in csv_ids.get(e["prefix"], set()):
        exclude_keys.add(e["key"])
    elif norm(e["image_url"]) in csv_urlset:
        exclude_keys.add(e["key"])

print("\nexcluded keys:", len(exclude_keys))
kept = [e for e in inv if e["key"] not in exclude_keys]
from collections import Counter
print("kept by prefix:", dict(Counter(e["prefix"] for e in kept)))
print("kept keys sample:", [e["key"] for e in kept[:30]])

# rectification candidates: CSV rows whose url maps to inventory prefix AND name/country looks wrong
print("\n== rectification candidates ==")
bad = []
for row in csv_rows:
    if row["pfx"] == "vit":
        continue  # names looked correct
    # garbled if name contains ' · ' pattern or country mismatch
    garbled = " · " in row["name"]
    bad.append((row["pfx"], row["idx"], row["csv_id"], row["country"], row["name"][:60], garbled))
from collections import Counter as C2
print("rows by pfx:", dict(C2(r[0] for r in bad)))
print("garbled count:", sum(1 for r in bad if r[5]))
for r in bad[:5]:
    print("   ", r)
g = [r for r in bad if r[5]]
print("garbled by pfx:", dict(C2(r[0] for r in g)))

json.dump({"excluded": sorted(exclude_keys),
           "csv_ids": {k: sorted(v) for k, v in csv_ids.items()}},
          open(os.path.join(ROOT, "_es_overlap2.json"), "w", encoding="utf-8"), indent=1)
