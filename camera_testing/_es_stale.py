# -*- coding: utf-8 -*-
"""Session 47: stale-id liveness, pre-host 176266, camarasdgt html structure."""
import json
import re
import urllib.request
import urllib.error

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Referer": "https://etraffic.dgt.es/etrafficWEB/"}


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read(400000)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read(4000)
    except Exception as e:
        return None, {}, str(e).encode()


prod = json.load(open(ROOT + r"\_es_camaras_etraffic.json", encoding="utf-8"))
old = json.load(open(ROOT + r"\_es_camaras_dgt.json", encoding="utf-8"))["camaras"]
old_map = {c["id"]: c for c in old}

only_old = ['168856', '176531', '176532', '176533', '176534', '176535', '176537', '178574', '18154', '181921', '181924']

print("== old-only ids on prod host ==")
alive = []
for cid in only_old:
    u = f"{prod['urlBase']}{cid}.jpg"
    st, h, b = fetch(u, timeout=20)
    is_img = st == 200 and "image" in h.get("Content-Type", "") and len(b) > 2000
    meta = old_map.get(cid, {})
    print(f"  {cid} {meta.get('carretera')} {meta.get('latitud')},{meta.get('longitud')} fecha={meta.get('fecha')} -> {st} {h.get('Content-Type')} len={len(b)} {'ALIVE' if is_img else ''} lm={h.get('Last-Modified')}")
    if is_img:
        alive.append(cid)
print("alive old-only:", alive)

print("\n== 176266 on pre host ==")
st, h, b = fetch("https://etraffic-pre.dgt.es/camarasEtraffic/176266.jpg", timeout=20)
print("pre img:", st, h.get("Content-Type"), len(b), "lm=", h.get("Last-Modified"))

print("\n== camarasdgt road html structure ==")
html = open(ROOT + r"\_es_camarasdgt_road.html", encoding="utf-8").read()
# img tags
imgs = re.findall(r"<img[^>]+>", html, re.I)
print("img tags:", len(imgs))
for t in imgs[:8]:
    print(" ", t[:250])
# iframes
ifr = re.findall(r"<iframe[^>]+>", html, re.I)
print("iframes:", len(ifr))
for t in ifr[:5]:
    print(" ", t[:250])
# camera links
links = re.findall(r'href="([^"]+)"[^>]*>([^<]{0,80})', html)
cam_links = [(a, b2.strip()) for a, b2 in links if re.search(r"camara|cam/", a, re.I) or "cámara" in b2.lower()]
print("cam links:", len(cam_links))
for a, b2 in cam_links[:15]:
    print(" ", a, "|", b2)
# any dgt/etraffic refs
refs = sorted(set(re.findall(r'https?://[^"\'\s<>]+dgt[^"\'\s<>]*', html)))
print("dgt refs:", refs[:15])
# look for section with camera list
m = re.search(r"(c[aá]maras?.{0,600})", html, re.I | re.S)
if m:
    print("context:", m.group(1)[:600])
