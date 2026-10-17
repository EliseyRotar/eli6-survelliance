# -*- coding: utf-8 -*-
"""Session 47: Catalonia XML/KML + gencat cam page + euskadi json fix + admins."""
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


print("== Catalonia ==")
for name, u in {
    "cat_xml": "http://www.gencat.cat/transit/opendata/cameres.xml",
    "cat_kml": "http://www.gencat.cat/transit/opendata/cameres.kml",
    "cat_page": "https://transit.gencat.cat/ca/informacio-viaria/estat-transit/cameres-transit/",
    "cat_socrata": "https://analisi.transparenciacatalunya.cat/resource/3tzz-6b9y.json?$limit=500",
}.items():
    st, h, b = fetch(u)
    print(name, "->", st, h.get("Content-Type"), len(b))
    if st == 200 and len(b) > 50:
        ext = u.rsplit(".", 1)[-1].split("?")[0]
        open(ROOT + f"\\_es_{name}.{ext}", "wb").write(b)

# inspect
import os
for f in ["_es_cat_xml.xml", "_es_cat_kml.kml"]:
    p = ROOT + "\\" + f
    if os.path.exists(p):
        t = open(p, encoding="utf-8", errors="replace").read()
        print(f"\n{f}: len", len(t))
        print("head:", t[:600].replace("\n", " ")[:600])
        print("cam tags:", len(re.findall(r"<", t)))
        m = re.findall(r"https?://[^<>\"'\s]+\.(?:jpg|png|gif|jpeg)", t, re.I)
        print("media urls:", len(m), m[:5])

# socrata json
p = ROOT + r"\_es_cat_socrata.json"
if os.path.exists(p):
    try:
        d = json.load(open(p, encoding="utf-8"))
        print("\nsocrata:", type(d).__name__, len(d))
        if d:
            print("item0:", json.dumps(d[0], ensure_ascii=False)[:600])
    except Exception as e:
        print("socrata parse:", e)

# gencat cam page hrefs
p = ROOT + r"\_es_cat_page.html"
if os.path.exists(p):
    t = open(p, encoding="utf-8", errors="replace").read()
    hrefs = sorted(set(re.findall(r'href="([^"]+)"', t)))
    interesting = [x for x in hrefs if re.search(r"jpg|png|gif|pdf|cam|imat|video|popup", x, re.I)]
    print("\ngencat page interesting hrefs:", len(interesting))
    for x in interesting[:40]:
        print(" ", x)

print("\n== Euskadi json raw ==")
raw = open(ROOT + r"\_es_euskadi_json.json", "rb").read(200)
print(raw[:200])

print("\n== euskadi admins dataset download links ==")
t = open(ROOT + r"\_es_euskadi_admins.html", encoding="utf-8", errors="replace").read()
links = sorted(set(re.findall(r'href="([^"]+)"', t)))
dls = [x for x in links if re.search(r"csv|json|xls|geojson|xml|descarrega|download|opendata", x, re.I)]
for x in dls[:40]:
    print(" ", x)
