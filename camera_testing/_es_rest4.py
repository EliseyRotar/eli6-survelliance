# -*- coding: utf-8 -*-
"""Session 47: andorra API + cantur webcams index + WAF bodies + vitoria image test."""
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


print("== andorra cameras API ==")
st, h, b = fetch("https://app.mobilitat.ad/api/v1/cameras", headers={"Referer": "https://www.mobilitat.ad/totes-les-cameres", "Accept": "application/json"}, timeout=40)
print("api:", st, h.get("Content-Type"), len(b))
if st == 200:
    open(ROOT + r"\_es_andorra_api.json", "wb").write(b)
    try:
        d = json.loads(b.decode("utf-8", "replace"))
        print(" type:", type(d).__name__)
        if isinstance(d, dict):
            print(" keys:", list(d.keys())[:10])
            arr = d.get("result") or d.get("cameras") or d.get("data") or []
            if isinstance(arr, list) and arr:
                print(" n:", len(arr))
                print(" item0:", json.dumps(arr[0], ensure_ascii=False, indent=1)[:700])
        elif isinstance(d, list):
            print(" n:", len(d))
            print(" item0:", json.dumps(d[0], ensure_ascii=False, indent=1)[:700])
    except Exception as e:
        print(" parse:", e, b[:300])
else:
    print(" body:", b[:400])

print("\n== cantur webcams index ==")
st, h, b = fetch("https://cantur.com/webcams/", timeout=40)
print("index:", st, len(b))
if st == 200:
    t = b.decode("utf-8", "replace")
    open(ROOT + r"\_es_cantur_webcams.html", "w", encoding="utf-8").write(t)
    links = sorted(set(re.findall(r'href="([^"]*webcam[^"]*)"', t, re.I)))
    print("webcam links:", links)
    imgs = sorted(set(re.findall(r'(?:src|href)="([^"]+/camaras/[^"]+)"', t, re.I)))
    print("imgs:", len(imgs))
    for x in imgs[:30]:
        print(" ", x)

print("\n== bizkaia 36B content ==")
st, h, b = fetch("https://www.opendatabizkaia.eus/es/datastore/dump/893256e6-3906-4740-a20c-4a874bf33f24/camaras-trafico-2020?format=json", timeout=30)
print(" ", st, b[:200])

print("\n== donostia/bilbao 403 bodies ==")
st, h, b = fetch("https://www.donostia.eus/datosabiertos/recursos/camaras-trafico/camarastraficocas.json",
                 headers={"Referer": "https://www.donostia.eus/es/datos-abiertos", "Accept": "application/json"}, timeout=30)
print("donostia:", st, b[:250])
st, h, b = fetch("https://www.bilbao.eus/aytoonline/srvDatasetCamaras?formato=geojson",
                 headers={"Referer": "https://www.bilbao.eus/", "Accept": "*/*"}, timeout=30)
print("bilbao:", st, b[:250])

print("\n== vitoria image test ==")
st, h, b = fetch("https://www.vitoria-gasteiz.org/c11-01w/cameras?action=get&id=CM06_ROI_4", timeout=30)
print(" img:", st, h.get("Content-Type"), len(b), "lm=", h.get("Last-Modified"))
