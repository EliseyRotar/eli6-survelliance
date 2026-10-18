# -*- coding: utf-8 -*-
import re

h = open(r"C:\Users\ELI6-A~1\AppData\Local\Temp\dn_od.html", encoding="utf-8", errors="replace").read()
print("len:", len(h))
links = sorted(set(re.findall(r"href=[\"']([^\"']+)[\"']", h)))
inter = [l for l in links if re.search(r"dataset|datosc|dades|api|csv|geojson|ckan|socrata|camar|transi|traf", l, re.I)]
print("total links:", len(links), "interesting:", len(inter))
for l in inter[:50]:
    print(" ", l[:150])
seen = set()
for m in re.finditer(r"([^>]{0,60}(?:camar|meres|trafico|nsit)[^<]{0,60})", h, re.I):
    s = re.sub(r"\s+", " ", m.group(1)).strip()
    if s and s not in seen:
        seen.add(s)
        print("TXT:", s[:150])
