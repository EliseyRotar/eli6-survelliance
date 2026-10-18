# -*- coding: utf-8 -*-
import json
import re

# 1) Donostia wayback geojson
b = open(r"C:\Users\ELI6-A~1\AppData\Local\Temp\ads_wayback.geojson", encoding="utf-8", errors="replace").read()
print("== ADS raw:", b[:150].replace("\n", " "))
try:
    i, j = b.find("{"), b.rfind("}")
    d = json.loads(b[i : j + 1])
    feats = d.get("features", [])
    print("ADS features:", len(feats))
    for f in feats:
        p = f.get("properties", {})
        g = f.get("geometry") or {}
        print("  ", json.dumps(p, ensure_ascii=False)[:280], "|", g.get("coordinates"))
except Exception as e:
    print("ADS ERR", e)

# 2) Bizkaia HTML resource table
h = open(r"C:\Users\ELI6-A~1\AppData\Local\Temp\bizk_od.html", encoding="utf-8", errors="replace").read()
print("== bizk html len", len(h))
rows = re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S | re.I)
print("tr rows:", len(rows))
camrows = []
for r in rows:
    cells = re.findall(r"<td[^>]*>(.*?)</td>", r, re.S | re.I)
    if not cells:
        continue
    vals = [re.sub(r"<[^>]+>|&nbsp;", "", c).strip() for c in cells]
    if any(re.search(r"cam\d+\.jpg|http.*cam", v, re.I) for v in vals):
        camrows.append(vals)
print("cam rows:", len(camrows))
for v in camrows[:5]:
    print("  ", v)
# any http jpg urls anywhere in page
urls = sorted(set(re.findall(r"https?://[^\"'<>\s]+\.(?:jpg|jpeg|png)", h, re.I)))
print("jpg urls in page:", len(urls))
for u in urls[:10]:
    print("  ", u[:140])
# pagination links
pag = [m.group(1) for m in re.finditer(r"href=[\"']([^\"']*(?:page|offset|pagina)[^\"']*)[\"']", h, re.I)]
print("pagination:", pag[:8])
