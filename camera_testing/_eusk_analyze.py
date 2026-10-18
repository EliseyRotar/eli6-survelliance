# -*- coding: utf-8 -*-
"""Session 47h: unified Euskadi open-data vs CSV analysis."""
import csv
import json
import re
from collections import defaultdict

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
CSV = ROOT + r"\controllable_Webcams.csv"
T = r"C:\Users\ELI6-A~1\AppData\Local\Temp"


def cam_id(url):
    m = re.search(r"camaras/(\d+)\s*\.jpg", url, re.I)
    if m:
        return "trk" + m.group(1)
    m = re.search(r"/cam(\d+)\.jpg", url, re.I)
    if m:
        return "bm" + m.group(1)
    m = re.search(r"codec(\d+)", url, re.I)
    if m:
        return "blb" + m.group(1)
    m = re.search(r"[?&]id=(\w+)", url, re.I)
    if m:
        return "vgz" + m.group(1)
    return None


# --- catalogs ---
cands = {}  # key -> record

# GV 131
b = open(T + r"\gv_cams.geojson", encoding="utf-8", errors="replace").read()
i, j = b.find("{"), b.rfind("}")
gv = json.loads(b[i : j + 1])
for f in gv["features"]:
    p = f["properties"]
    url = p.get("url cam", "")
    k = cam_id(url)
    if not k:
        continue
    g = f.get("geometry") or {}
    xy = g.get("coordinates") or [None, None]
    cands.setdefault(k, {"url": url, "lat": xy[1], "lon": xy[0], "src": []})
    cands[k]["src"].append("gv")
    cands[k].setdefault("gv_name", p.get("title"))
    cands[k].setdefault("gv_road", p.get("road"))
    cands[k].setdefault("gv_pk", p.get("pk"))

# AVG 40
avg = json.load(open(T + r"\avg_cams.geojson", encoding="utf-8"))
for f in avg["features"]:
    p = f["properties"]
    url = p.get("imagen", "")
    k = cam_id(url)
    if not k:
        continue
    xy = (f.get("geometry") or {}).get("coordinates") or [None, None]
    cands.setdefault(k, {"url": url, "lat": xy[1], "lon": xy[0], "src": []})
    cands[k]["src"].append("avg")
    cands[k].setdefault("avg_name", p.get("nombre"))
    cands[k].setdefault("avg_comm", p.get("commStatusCode"))

# ADS 6 (wayback geojson)
ads = json.load(open(T + r"\ads_wayback.geojson", encoding="latin-1"))
for f in ads["features"]:
    p = f["properties"]
    url = p.get("Imagen", "")
    k = cam_id(url)
    if not k:
        continue
    xy = (f.get("geometry") or {}).get("coordinates") or [None, None]
    cands.setdefault(k, {"url": url, "lat": xy[1], "lon": xy[0], "src": []})
    cands[k]["src"].append("ads")
    cands[k].setdefault("ads_name", p.get("Nombre"))
    cands[k].setdefault("ads_road", p.get("Carretera"))
    cands[k].setdefault("ads_pk", p.get("PK"))

# AB Bilbao 119
ab = json.load(open(T + r"\ab_wayback.geojson", encoding="utf-8"))
for f in ab["features"]:
    p = f["properties"]
    url = p.get("URL", "")
    k = cam_id(url)
    if not k:
        continue
    xy = (f.get("geometry") or {}).get("coordinates") or [None, None]
    cands.setdefault(k, {"url": url, "lat": xy[1], "lon": xy[0], "src": []})
    cands[k]["src"].append("ab")
    cands[k].setdefault("ab_name", p.get("Nombre"))
    cands[k].setdefault("ab_tipo", p.get("Tipo"))

# DFB 226 csv
import io

b = open(T + r"\dfb_en.csv", encoding="utf-8-sig", errors="replace").read()
for r in csv.DictReader(io.StringIO(b)):
    url = (r.get("URL") or "").strip()
    if not url.startswith("http"):
        continue
    k = cam_id(url)
    if not k:
        continue
    lat = (r.get("KOORD_GEOGRAFIKOAK_LATITUDEA/COORD_GEOGRAFICAS_LATITUD") or "").replace(",", ".")
    lon = (r.get("KOORD_GEOGRAFIKOAK_LONGITUDEA/COORD_GEOGRAFICAS_LONGITUD") or "").replace(",", ".")
    cands.setdefault(k, {"url": url, "lat": float(lat) if lat else None, "lon": float(lon) if lon else None, "src": []})
    cands[k]["src"].append("dfb")
    cands[k].setdefault("dfb_name", r.get("IZENA/NOMBRE"))
    cands[k].setdefault("dfb_road", r.get("ERREPIDEA/CARRETERA"))
    cands[k].setdefault("dfb_pk", r.get("PK"))
    cands[k].setdefault("dfb_ent", r.get("ENTITATEA_CAS/ENTIDAD_CAS"))

print("=== catalog union:", len(cands))
bysrc = defaultdict(int)
for v in cands.values():
    for s in set(v["src"]):
        bysrc[s] += 1
print("by source:", dict(bysrc))

# --- CSV ---
JUNK = re.compile(r"·\s*Apps\b|·\s*#|apps\.trafikoa")
rows = []
by_id = defaultdict(list)
url_set = set()
with open(CSV, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        rows.append(r)
        u = (r.get("live_stream_url") or "").strip()
        if u:
            url_set.add(u.rstrip("/"))
        k = cam_id(u) or cam_id(r.get("url") or "")
        if k:
            by_id[k].append(r)

print("=== CSV rows:", len(rows))

# overlap by exact url (host matters) and by cam id (host-insensitive)
new_by_id = [k for k in cands if k not in by_id]
print("camids in catalog not in CSV:", len(new_by_id))
for k in new_by_id[:40]:
    v = cands[k]
    print("  NEW", k, "|", (v.get("gv_name") or v.get("ab_name") or v.get("dfb_name") or v.get("avg_name") or v.get("ads_name")), "|", v["url"][:90], "| src", v["src"])

overlap = [k for k in cands if k in by_id]
print("camids overlapping CSV:", len(overlap))
# host-diff (same cam id, but catalog url host differs from csv url)
hostdiff = 0
for k in overlap:
    cu = (by_id[k][0].get("live_stream_url") or "").strip()
    if cu.rstrip("/") != cands[k]["url"].rstrip("/"):
        hostdiff += 1
print("  of which url differs (host/normalization):", hostdiff)

# junk titles among overlapping trafikoa/bizkaimove/bilbao rows
junk = []
for k, rs in by_id.items():
    for r in rs:
        t = r.get("project_name") or ""
        if JUNK.search(t) or "Apps ·" in t:
            junk.append(r)
print("=== junk-titled (Apps) rows among cam-id rows:", len(junk))
# junk rows overall in csv for these hosts
junk_all = []
with open(CSV, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        u = ((r.get("live_stream_url") or "") + " " + (r.get("url") or "")).lower()
        t = r.get("project_name") or ""
        if ("trafikoa" in u or "bizkaimove" in u or "bilbao.eus" in u or "vitoria-gasteiz" in u) and ("Apps ·" in t or "· #" in t):
            junk_all.append(r["csv_id"])
print("junk-titled rows across those hosts:", len(junk_all))

# missing coords among matched rows
nocoord = sum(1 for k in overlap for r in by_id[k] if not (r.get("lat") and r.get("lon")))
print("matched csv rows missing coords:", nocoord)
