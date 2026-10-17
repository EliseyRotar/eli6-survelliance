# -*- coding: utf-8 -*-
"""Extract fetch call construction for API endpoints."""
import re

PATH = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\_es_etraffic_index.js"
js = open(PATH, encoding="utf-8", errors="replace").read()

# find each endpoint literal and wider context
for ep in ["getCamaras", "getFilteredData", "getPMVs", "getCampanyas", "getLeyendaCache", "getPMVDatos"]:
    for m in re.finditer(re.escape(ep), js):
        s = max(0, m.start() - 500)
        e = min(len(js), m.end() + 500)
        print(f"===== {ep} @ {m.start()} =====")
        print(re.sub(r"\s+", " ", js[s:e]))
        print()
