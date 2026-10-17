# -*- coding: utf-8 -*-
"""Find API fetch calls in eTraffic JS."""
import re

PATH = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\_es_etraffic_index.js"
js = open(PATH, encoding="utf-8", errors="replace").read()

# context around /etrafficWEB/api
for m in re.finditer(r"etrafficWEB/api", js):
    s = max(0, m.start() - 300)
    e = min(len(js), m.end() + 400)
    print("== api ctx ==")
    print(re.sub(r"\s+", " ", js[s:e]))
    print()

# fetch( and axios
for pat in [r"fetch\(", r"axios", r"XMLHttpRequest", r"\.get\(", r"\.post\("]:
    print(f"-- {pat}: {len(list(re.finditer(pat, js)))} hits")

# template literals containing api
for m in re.finditer(r"[`'\"][^`'\"]*api[^`'\"]*[`'\"]", js, re.I):
    print("  api-lit:", m.group(0)[:200])

# urlBaseCamaras context
for m in re.finditer(r"urlBaseCamaras", js):
    s = max(0, m.start() - 250)
    e = min(len(js), m.end() + 250)
    print("== urlBaseCamaras ctx ==")
    print(re.sub(r"\s+", " ", js[s:e]))
    print()

# any occurrence of 'incidencias' endpoint-ish
for m in re.finditer(r"incidencias|eventos|trafico|consultar|Consulta", js):
    pass
# look for string literals with slashes that look like endpoints
lits = sorted(set(re.findall(r"[\"'`](/[a-zA-Z0-9][a-zA-Z0-9._/-]{2,80})[\"'`]", js)))
print("all slash lits:", lits)
# and backtick template endpoints
tpl = sorted(set(re.findall(r"[\"'`](\$\{[^}]{1,60}\}[a-zA-Z0-9._/-]{0,60})[\"'`]", js)))
print("tpl lits:", tpl[:60])
