# -*- coding: utf-8 -*-
"""Session 47: fetch Euskadi open-data camera datasets + probes."""
import json
import re
import urllib.request
import urllib.error

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read(4000)
    except Exception as e:
        return None, {}, str(e).encode()


urls = {
    "euskadi_csv": "https://opendata.euskadi.eus/contenidos/ds_localizaciones/camaras_trafico/opendata/camaras-trafico.csv",
    "euskadi_json": "https://opendata.euskadi.eus/contenidos/ds_localizaciones/camaras_trafico/opendata/camaras-trafico.json",
    "euskadi_admins": "https://opendata.euskadi.eus/catalogo/-/camaras-de-trafico-de-las-administraciones-publicas-de-euskadi/",
}
for name, u in urls.items():
    st, h, b = fetch(u)
    print(name, "->", st, h.get("Content-Type"), len(b))
    if st == 200 and len(b) > 100:
        ext = "csv" if "csv" in u else ("json" if "json" in u else "html")
        open(ROOT + f"\\_es_{name}.{ext}", "wb").write(b)

# inspect csv
try:
    txt = open(ROOT + r"\_es_euskadi_csv.csv", encoding="utf-8", errors="replace").read()
    lines = [l for l in txt.splitlines() if l.strip()]
    print("csv lines:", len(lines))
    print("header:", lines[0])
    print("row1:", lines[1])
    print("last:", lines[-1])
except Exception as e:
    print("csv read fail:", e)

try:
    d = json.load(open(ROOT + r"\_es_euskadi_json.json", encoding="utf-8", errors="replace"))
    print("json type:", type(d).__name__, (len(d) if hasattr(d, "__len__") else ""))
    if isinstance(d, dict):
        print("keys:", list(d.keys())[:10])
        for k, v in d.items():
            if isinstance(v, list) and v:
                print(f"  {k}[0]:", json.dumps(v[0], ensure_ascii=False)[:400])
                print(f"  {k} n:", len(v))
                break
    elif isinstance(d, list):
        print("item0:", json.dumps(d[0], ensure_ascii=False)[:400])
except Exception as e:
    print("json read fail:", e)
