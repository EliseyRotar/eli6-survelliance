# -*- coding: utf-8 -*-
"""Session 47: image verification + parallel source comparison."""
import json
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Referer": "https://etraffic.dgt.es/etrafficWEB/"}


def fetch(url, timeout=25, headers=None):
    hh = dict(UA)
    if headers:
        hh.update(headers)
    req = urllib.request.Request(url, headers=hh)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read(600000)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read(4000)
    except Exception as e:
        return None, {}, str(e).encode()


d = json.load(open(ROOT + r"\_es_camaras_etraffic.json", encoding="utf-8"))
cams = d["camaras"]
base = d["urlBase"]
print("cams:", len(cams), "base:", base)

# 1) sample image checks (20 spread across list)
sample = [cams[i] for i in range(0, len(cams), max(1, len(cams) // 20))][:20]
ok = bad = 0
last_mods = []
for c in sample:
    url = f"{base}{c['idCamara']}.jpg"
    st, h, b = fetch(url, timeout=20)
    img = st == 200 and (h.get("Content-Type", "").startswith("image") and len(b) > 2000)
    if img:
        ok += 1
        last_mods.append((c["idCamara"], h.get("Last-Modified"), len(b), h.get("Server"), h.get("Content-Type")))
    else:
        bad += 1
        print("  BAD", url, st, h.get("Content-Type"), b[:80])
print(f"image sample: ok={ok} bad={bad}")
for x in last_mods[:8]:
    print("  ", x)

# full inventory of image URLs - just check id formats
ids = [c["idCamara"] for c in cams]
print("id lengths:", sorted({len(i) for i in ids}))
print("id sample:", ids[:10])

# 2) load old camaras.json (dgt.es) for comparison
try:
    old = json.load(open(ROOT + r"\_es_camaras_dgt.json", encoding="utf-8"))
    print("\nold camaras.json type:", type(old).__name__)
    if isinstance(old, dict):
        print("keys:", list(old.keys())[:10])
        for k, v in old.items():
            if isinstance(v, list) and v:
                print(f"  {k}: n={len(v)} sample=", json.dumps(v[0], ensure_ascii=False)[:400])
                break
    elif isinstance(old, list):
        print("n:", len(old), "sample:", json.dumps(old[0], ensure_ascii=False)[:500])
except Exception as e:
    print("old json fail:", e)

# 3) DATEX2 v3.7 device publication
print("\n== DATEX2 v3.7 ==")
st, h, b = fetch("https://nap.dgt.es/datex2/v3/dgt/DevicePublication/camaras_datex2_v37.xml", timeout=90)
print("nap datex2:", st, h.get("Content-Type"), len(b))
if st == 200:
    open(ROOT + r"\_es_datex2_v37.xml", "wb").write(b)
else:
    print(b[:200])

# 4) other candidate endpoints
print("\n== alt endpoints ==")
for url in [
    "https://www.dgt.es/.content/.assets/json/camaras.json",
    "http://infocar.dgt.es/datex2/dgt/CCTVSiteTablePublication/all/content.xml",
    "https://infocar.dgt.es/datex2/dgt/CCTVSiteTablePublication/all/content.xml",
    "https://etraffic.dgt.es/camarasEtraffic/",
    "https://etraffic.dgt.es/camarasEtraffic/176130.jpg",
]:
    st, h, b = fetch(url, timeout=25)
    print(f"  {url} -> {st} {h.get('Content-Type')} len={len(b)} server={h.get('Server')}")
