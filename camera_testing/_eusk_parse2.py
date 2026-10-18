# -*- coding: utf-8 -*-
import json
import re

d = json.load(open(r"C:\Users\ELI6-A~1\AppData\Local\Temp\euskadi_cams.json", encoding="utf-8"))
print("== euskadi index:", len(d))
for e in d:
    print("-", e.get("sourceId"), "|", e.get("sourceEs"), "|", e.get("datasetTitleEs"))
    print("   file:", e.get("fileUrl"))

# Donostia page embeds
h = open(r"C:\Users\ELI6-A~1\AppData\Local\Temp\dn_cams.html", encoding="utf-8", errors="replace").read()
print("== dn_cams embeds")
for m in re.finditer(r"<iframe[^>]*>", h, re.I):
    print(" IFRAME:", m.group(0)[:260])
for m in re.finditer(r"id=[\"']([^\"']+)[\"']", h):
    v = m.group(1)
    if re.search(r"cam|map|geo|viewer|bisorea", v, re.I):
        print(" ID:", v)
for m in re.finditer(r"([\w./:?=&%-]*(?:fwCamaras|camaras_trafico|nsf)[\w./:?=&%-]*)", h):
    print(" REF:", m.group(1)[:170])
# body text around 'cámara'
txt = re.sub(r"<script.*?</script>|<style.*?</style>", " ", h, flags=re.S | re.I)
txt = re.sub(r"<[^>]+>", " ", txt)
txt = re.sub(r"\s+", " ", txt)
i = txt.find("Cámaras de tráfico")
print(" TEXT:", txt[i : i + 900] if i >= 0 else txt[:400])

# Gipuzkoa page embeds
g = open(r"C:\Users\ELI6-A~1\AppData\Local\Temp\gip_webcams.html", encoding="utf-8", errors="replace").read()
print("== gipuzkoa embeds")
for m in re.finditer(r"<iframe[^>]*>", g, re.I):
    print(" IFRAME:", m.group(0)[:260])
seen = set()
for m in re.finditer(r"(?:src|data-src|href)=[\"']([^\"']+)[\"']", g, re.I):
    u = m.group(1)
    if re.search(r"webcam|hondartza|camera|cmar|irudi|image|embed|apps\.", u, re.I) and u not in seen:
        seen.add(u)
        print(" URL:", u[:180])
txt2 = re.sub(r"<script.*?</script>|<style.*?</style>", " ", g, flags=re.S | re.I)
txt2 = re.sub(r"<[^>]+>", " ", txt2)
txt2 = re.sub(r"\s+", " ", txt2)
i2 = txt2.find("Webcams")
print(" TEXT:", txt2[i2 : i2 + 1400] if i2 >= 0 else "")
