# -*- coding: utf-8 -*-
"""Session 47: DATEX2 ids for extras, camarasdgt content, final probes."""
import json
import re

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"

# DATEX2: map id -> device block fields
txt = open(ROOT + r"\_es_datex2_v37.xml", encoding="utf-8", errors="replace").read()
blocks = re.findall(r'<ns2:device[^>]*id="(\d+)"[^>]*>(.*?)</ns2:device>', txt, re.S)
print("datex2 devices:", len(blocks))
datex_ids = {b[0] for b in blocks}
for want in ["18", "103", "1040", "993", "164258"]:
    print(f"  id {want} in datex2:", want in datex_ids)

# camarasdgt content beyond nav
html = open(ROOT + r"\_es_camarasdgt_road.html", encoding="utf-8").read()
# find all h3/h4 or card titles
cards = re.findall(r'<div class="card[^"]*".{0,1200}?</div>', html, re.S)
print("\ncamarasdgt cards:", len(cards))
for c in cards[:3]:
    print("  CARD:", re.sub(r"\s+", " ", c)[:600])
    print("  ---")
# look for 'data-' image holders
holders = re.findall(r'<[^>]*(?:data-src|data-image|data-camara|data-id)[^>]*>', html, re.I)
print("data holders:", holders[:10])
# find where the road cameras appear: search 'A-2' occurrences after nav
idx = html.rfind("</nav>")
body = html[idx:]
print("\nbody after nav len:", len(body))
print(re.sub(r"\s+", " ", body)[:4000])
