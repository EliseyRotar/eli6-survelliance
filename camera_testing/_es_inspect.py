# -*- coding: utf-8 -*-
"""Inspect source file structures."""
import json
import os

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
for name in ["_es_camaras_etraffic.json", "_es_camaras_dgt.json", "_es_camaras_pre.json",
             "_es_euskadi.geojson", "_es_cat_cams.json", "_es_vitoria.geojson",
             "_es_andorra_api.json", "_es_cantur_pages.json", "_es_webcam_yt_ids.json",
             "_es_hist_liveness.json", "_es_euskadi_csv.csv"]:
    p = os.path.join(ROOT, name)
    if not os.path.exists(p):
        print(name, "-> MISSING")
        continue
    if name.endswith(".csv"):
        with open(p, encoding="utf-8") as f:
            head = [next(f) for _ in range(3)]
        print(f"\n== {name} ({os.path.getsize(p)} B) lines:")
        for h in head:
            print("   ", h.rstrip()[:250])
        continue
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception as e:
        print(name, "-> parse err", e)
        continue
    print(f"\n== {name} ({os.path.getsize(p)} B): {type(d).__name__}")
    if isinstance(d, dict):
        print("   keys:", list(d.keys())[:10])
        for k, v in list(d.items())[:3]:
            print(f"   [{k}] -> {json.dumps(v, ensure_ascii=False)[:300]}")
    elif isinstance(d, list):
        print("   len:", len(d))
        for v in d[:2]:
            print("   item:", json.dumps(v, ensure_ascii=False)[:400])
