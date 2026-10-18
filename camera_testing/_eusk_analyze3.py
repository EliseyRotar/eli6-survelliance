# -*- coding: utf-8 -*-
import csv
import html
import json
import re
import unicodedata
from collections import defaultdict

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
CSV = ROOT + r"\controllable_Webcams.csv"
T = r"C:\Users\ELI6-A~1\AppData\Local\Temp"


def norm(s):
    s = html.unescape(s or "")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9]+", " ", s).upper().strip()
    return s


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
    m = re.search(r"CamarasMunicipales/(\d+)", url, re.I)
    if m:
        return "geo" + m.group(1)
    return None


# catalog
ab = json.load(open(T + r"\ab_wayback.geojson", encoding="utf-8"))
cat_blb = {}
for f in ab["features"]:
    p = f["properties"]
    k = cam_id(p.get("URL", ""))
    xy = (f.get("geometry") or {}).get("coordinates") or [None, None]
    cat_blb[k] = {"name": p.get("Nombre") or "", "tipo": p.get("Tipo") or "", "url": p.get("URL"), "lat": xy[1], "lon": xy[0]}
print("catalog bilbao:", len(cat_blb))

gv = json.loads(open(T + r"\gv_cams.geojson", encoding="utf-8", errors="replace").read().split("jsonCallback(", 1)[1].rsplit(")", 1)[0])
cat_trk = {}
for f in gv["features"]:
    p = f["properties"]
    k = cam_id(p.get("url cam", ""))
    xy = (f.get("geometry") or {}).get("coordinates") or [None, None]
    cat_trk[k] = {"name": p.get("title"), "road": p.get("road"), "pk": p.get("pk"), "url": p.get("url cam"), "lat": xy[1], "lon": xy[0]}
print("catalog trafikoa(gv):", len(cat_trk))

import io

b = open(T + r"\dfb_en.csv", encoding="utf-8-sig", errors="replace").read()
cat_bm = {}
for r in csv.DictReader(io.StringIO(b)):
    u = (r.get("URL") or "").strip()
    if not u.startswith("http"):
        continue
    k = cam_id(u)
    lat = (r.get("KOORD_GEOGRAFIKOAK_LATITUDEA/COORD_GEOGRAFICAS_LATITUD") or "").replace(",", ".")
    lon = (r.get("KOORD_GEOGRAFIKOAK_LONGITUDEA/COORD_GEOGRAFICAS_LONGITUD") or "").replace(",", ".")
    cat_bm[k] = {"name": r.get("IZENA/NOMBRE") or "", "road": r.get("ERREPIDEA/CARRETERA"), "pk": r.get("PK"), "ent": r.get("ENTITATEA_CAS/ENTIDAD_CAS"), "url": u, "lat": float(lat) if lat else None, "lon": float(lon) if lon else None}
print("catalog bizkaimove:", len(cat_bm))

# csv scoped
rows = {"trk": [], "bm": [], "blb": [], "vgz": [], "geo": []}
junk_apps = []
junk_bm = []
with open(CSV, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        u = (r.get("live_stream_url") or "") + " " + (r.get("url") or "")
        ul = u.lower()
        t = r.get("project_name") or ""
        if "trafikoa" in ul or "bizkaimove" in ul or "vitoria-gasteiz" in ul or "geobilbao" in ul:
            k = cam_id(u)
            if k and k[:3] in rows:
                rows[k[:3]].append(r)
            if "Apps" in t:
                junk_apps.append(r)
            if "Bizkaimove" in t and "·" in t:
                junk_bm.append(r)

print("csv trk:", len(rows["trk"]), "| bm:", len(rows["bm"]), "| blb:", len(rows["blb"]), "| geo:", len(rows["geo"]), "| vgz:", len(rows["vgz"]))
print("junk Apps (trafikoa disc):", len(junk_apps), "| junk Bizkaimove disc:", len(junk_bm))

# trafikoa true-new
ids_csv = set("trk" + re.search(r"camaras/(\d+)", (r.get("live_stream_url") or "")).group(1) for r in rows["trk"] if re.search(r"camaras/(\d+)", r.get("live_stream_url") or ""))
new_trk = sorted(set(cat_trk) - ids_csv, key=lambda x: int(x[3:]))
print("GV truly-new trk ids:", new_trk)

# bizkaimove: new ids
ids_bm = set("bm" + re.search(r"/cam(\d+)", (r.get("live_stream_url") or "")).group(1) for r in rows["bm"] if re.search(r"/cam(\d+)", r.get("live_stream_url") or ""))
new_bm = sorted(set(cat_bm) - ids_bm, key=lambda x: int(x[2:]))
print("DFB truly-new bm ids:", len(new_bm), new_bm[:60])

# bilbao: name-based matching (catalog blb vs existing geo rows)
geo_names = set(norm(r.get("project_name") or "") for r in rows["geo"])
# strip common suffixes already in name like (Sabino Arana/Av...
unmatched = []
matched = 0
for k, v in cat_blb.items():
    n = norm(v["name"])
    hit = False
    if n in geo_names:
        hit = True
    else:
        for gn in geo_names:
            if n and (n in gn or gn in n):
                hit = True
                break
    if hit:
        matched += 1
    else:
        unmatched.append((k, v))
print("bilbao catalog matched-to-existing:", matched, "| unmatched (new candidates):", len(unmatched))
for k, v in unmatched:
    print("  NEW-BLB", k, "|", html.unescape(v["name"]), "|", v["tipo"], "|", v["url"][:80], "|", v["lat"], v["lon"])
