# -*- coding: utf-8 -*-
"""Mine eTraffic JS bundle for API endpoints."""
import re

PATH = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\_es_etraffic_index.js"
js = open(PATH, encoding="utf-8", errors="replace").read()

urls = sorted(set(re.findall(r"https?://[a-zA-Z0-9._~:/?#@!$&*+,;=%-]+", js)))
print("URLS:", len(urls))
for u in urls:
    print(" ", u)

paths = sorted(set(re.findall(r"[\"'](/[a-zA-Z0-9._/-]{3,100})[\"']", js)))
print("\nPATHS:", len(paths))
for p in paths:
    print(" ", p)

# keywords
for kw in ("camara", "camera", "cctv", "video", "mjpeg", "stream", "image", "iframe", "webservice", "api/", "json", "geojson", "wms", "tile"):
    hits = []
    for m in re.finditer(re.escape(kw), js, re.I):
        s = max(0, m.start() - 70)
        e = min(len(js), m.end() + 70)
        hits.append(re.sub(r"\s+", " ", js[s:e]))
    if hits:
        print(f"\n== kw={kw} ({len(hits)}) ==")
        for h in hits[:12]:
            print("  ...", h, "...")
