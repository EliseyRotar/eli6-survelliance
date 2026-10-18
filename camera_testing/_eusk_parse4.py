# -*- coding: utf-8 -*-
import re

h = open(r"C:\Users\ELI6-A~1\AppData\Local\Temp\bizk_od.html", encoding="utf-8", errors="replace").read()
for m in re.finditer(r".{100}226.{100}", h):
    s = re.sub(r"\s+", " ", m.group(0))
    print("CTX:", s[:230])
seen = set()
for m in re.finditer(r"href=[\"']([^\"']*\?[^\"']*)[\"']", h):
    u = m.group(1)
    if re.search(r"page|offset|start|despl|sigu|cont|pagesize|rows", u, re.I) and u not in seen:
        seen.add(u)
        print("PAG?", u[:190])
# look for 'resultados de un total'
for m in re.finditer(r".{80}resultados.{80}", h, re.I):
    print("RES:", re.sub(r"\s+", " ", m.group(0))[:200])
