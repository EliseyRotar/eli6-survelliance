# -*- coding: utf-8 -*-
"""Session 47: andorra all-cams, euskadi geojson parse, donostia/bilbao retry, trafikoa error, cantur index."""
import json
import re
import urllib.request
import urllib.error

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}


def fetch(url, timeout=60, headers=None):
    hh = dict(UA)
    if headers:
        hh.update(headers)
    req = urllib.request.Request(url, headers=hh)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read(4000)
    except Exception as e:
        return None, {}, repr(e).encode()


print("== euskadi geojson parse ==")
raw = open(ROOT + r"\_es_adm_camaras_trafico_geojson", "rb").read()
txt = raw.decode("utf-8-sig", "replace")
txt = re.sub(r"^\s*jsonCallback\(", "", txt)
txt = re.sub(r"\);\s*$", "", txt.strip())
try:
    d = json.loads(txt)
    print("type:", type(d).__name__)
    if isinstance(d, dict):
        print("keys:", list(d.keys()))
        fs = d.get("features", [])
        print("features:", len(fs))
        if fs:
            print("f0:", json.dumps(fs[0], ensure_ascii=False)[:500])
        json.dump(d, open(ROOT + r"\_es_euskadi.geojson", "w", encoding="utf-8"), ensure_ascii=False)
    elif isinstance(d, list):
        print("n:", len(d), "item0:", json.dumps(d[0], ensure_ascii=False)[:500])
        json.dump(d, open(ROOT + r"\_es_euskadi_list.json", "w", encoding="utf-8"), ensure_ascii=False)
except Exception as e:
    print("parse fail:", e, txt[:200])

print("\n== andorra totes-les-cameres ==")
st, h, b = fetch("https://www.mobilitat.ad/totes-les-cameres", timeout=30)
print("page:", st, len(b))
if st == 200:
    t = b.decode("utf-8", "replace")
    open(ROOT + r"\_es_andorra_cams.html", "w", encoding="utf-8").write(t)
    imgs = sorted(set(re.findall(r'(?:src|href)="([^"]+\.(?:gif|jpg|png)[^"]*)"', t, re.I)))
    print("imgs:", len(imgs))
    for x in imgs[:40]:
        print(" ", x)
    # data endpoints
    js = sorted(set(re.findall(r'["\'](/[^"\']*(?:api|json|cam)[^"\']*)["\']', t, re.I)))
    print("js refs:", js[:20])
    # inline cam objects
    hits = re.findall(r'\{[^{}]*"?(?:nom|name|url)"?[^{}]{0,300}\}', t)
    print("obj hits:", len(hits))
    for x in hits[:5]:
        print("  ", x[:300])

print("\n== donostia/bilbao retry ==")
for u, hdrs in [
    ("https://www.donostia.eus/datosabiertos/recursos/camaras-trafico/camarastraficocas.json",
     {"Referer": "https://www.donostia.eus/", "Accept": "application/json"}),
    ("https://www.bilbao.eus/aytoonline/srvDatasetCamaras?formato=geojson",
     {"Referer": "https://www.bilbao.eus/", "Accept": "application/json,geojson,*/*"}),
    ("https://www.opendatabizkaia.eus/es/datastore/dump/893256e6-3906-4740-a20c-4a874bf33f24/camaras-trafico-2020?format=json",
     {"Referer": "https://www.opendatabizkaia.eus/"}),
]:
    st, h, b = fetch(u, headers=hdrs, timeout=40)
    print(" ", u[:80], "->", st, h.get("Content-Type"), len(b))
    if st == 200 and len(b) > 50:
        name = re.sub(r"\W+", "_", u.rsplit("/", 1)[-1])[:50]
        open(ROOT + f"\\_es_{name}", "wb").write(b)
        print("    head:", b[:300])

print("\n== trafikoa error detail ==")
st, h, b = fetch("https://www.trafikoa.eus/static/files/tr/camaras/819.jpg", timeout=25)
print(" ", b)

print("\n== cantur cam index ==")
st, h, b = fetch("https://cantur.com/", timeout=40)
if st == 200:
    t = b.decode("utf-8", "replace")
    paths = sorted(set(re.findall(r'["\'](https?://cantur\.com/camaras/[^"\']+)["\']', t, re.I)))
    paths += sorted(set(re.findall(r'["\'](/camaras/[^"\']+)["\']', t, re.I)))
    print("cam paths:", len(paths))
    for x in paths[:50]:
        print(" ", x)
    # nav links containing cam
    hrefs = sorted(set(re.findall(r'href="([^"]+)"', t)))
    cand = [x for x in hrefs if "camar" in x.lower() or "webcam" in x.lower()]
    print("nav cam links:", cand[:20])
