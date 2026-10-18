# -*- coding: utf-8 -*-
import csv
import json
import re

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
rows = json.load(open(r"C:\Users\ELI6-A~1\AppData\Local\Temp\fgc_ods_rows.json", encoding="utf-8"))
recs = rows.get("records", [])
out = []
for r in recs:
    f = r["fields"]
    coord = f.get("coordenadas")
    lat = lon = None
    if isinstance(coord, list) and len(coord) == 2:
        lat, lon = coord[0], coord[1]
    elif isinstance(coord, dict):
        if isinstance(coord.get("coordinates"), list):
            lon, lat = coord["coordinates"][0], coord["coordinates"][1]
        else:
            lon, lat = coord.get("lon"), coord.get("lat")
    out.append({
        "id": f.get("id"),
        "business_unit": f.get("business_unit"),
        "name_bu": f.get("name_bu"),
        "tipus_servei": f.get("tipus_servei"),
        "nom_servei": f.get("nom_servei"),
        "is_active": f.get("is_active"),
        "url": f.get("url"),
        "imatge_2": (f.get("imatge_2") or {}).get("filename") if isinstance(f.get("imatge_2"), dict) else f.get("imatge_2"),
        "imatge_2_id": (f.get("imatge_2") or {}).get("id") if isinstance(f.get("imatge_2"), dict) else None,
        "lat": lat,
        "lon": lon,
        "recordid": r.get("recordid"),
    })
print("records:", len(out))
print("active:", sum(1 for o in out if o["is_active"] == 1), "| with url:", sum(1 for o in out if o["url"]))
print("with coords:", sum(1 for o in out if o["lat"] and o["lon"]))
tips = {}
for o in out:
    tips[o["tipus_servei"]] = tips.get(o["tipus_servei"], 0) + 1
print("tipus:", tips)
for o in out[:6]:
    print(" ", o["id"], o["name_bu"], "|", o["nom_servei"], "|", o["url"][:70] if o["url"] else None, "|", o["lat"], o["lon"], "| act", o["is_active"])

# overlap vs CSV
keys = set()
with open(ROOT + r"\controllable_Webcams.csv", newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        u = (r["live_stream_url"] or "") + " " + (r["url"] or "")
        if "projecte4estacions" in u or "fgc" in u.lower():
            keys.add((r["csv_id"], (r["project_name"] or "")[:40], (r["live_stream_url"] or r["url"])[:70]))
print("csv rows mentioning fgc/projecte4estacions:", len(keys))
for k in list(keys)[:10]:
    print("  ", k)
json.dump(out, open(ROOT + r"\camera_testing\_es_fgc_catalog.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("saved _es_fgc_catalog.json")
