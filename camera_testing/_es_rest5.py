# -*- coding: utf-8 -*-
"""Session 47: cantur pages + trafikoa retry + cat freshness."""
import hashlib
import json
import re
import time
import urllib.request
import urllib.error

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}


def fetch(url, timeout=45, headers=None):
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


print("== cantur webcam pages ==")
pages = ["abra-de-pas", "calgosa", "el-chivo2", "fuente-de", "sierra-del-hijar", "tres-mares"]
out = {}
for p in pages:
    st, h, b = fetch(f"https://cantur.com/webcam/{p}/", timeout=40)
    if st != 200:
        print(" ", p, "->", st)
        continue
    t = b.decode("utf-8", "replace")
    imgs = re.findall(r'(?:src|href|data-src)="([^"]+/camaras/[^"]+\.(?:jpg|png|gif)[^"]*)"', t, re.I)
    if not imgs:
        imgs = re.findall(r'https?://cantur\.com/camaras/[^"\'\s>]+\.(?:jpg|png|gif)', t, re.I)
    title = re.search(r"<title>(.*?)</title>", t, re.S | re.I)
    out[p] = {"imgs": sorted(set(imgs)), "title": title.group(1).strip() if title else ""}
    print(" ", p, "->", st, "imgs:", sorted(set(imgs))[:6], "| title:", out[p]["title"][:60])
json.dump(out, open(ROOT + r"\_es_cantur_pages.json", "w", encoding="utf-8"), indent=1)

print("\n== trafikoa retry ==")
for u in ["https://www.trafikoa.eus/static/files/tr/camaras/819.jpg",
          "https://apps.trafikoa.euskadi.eus/static/files/tr/camaras/102.jpg",
          "http://apps.trafikoa.euskadi.eus/static/files/tr/camaras/102.jpg"]:
    st, h, b = fetch(u, timeout=20)
    print(" ", u, "->", st, h.get("Content-Type"), len(b), str(b[:80]))

print("\n== cat freshness (2 fetches 45s apart) ==")
u = "http://mct.gencat.cat/mct2bo/RenderService?sctidcam=nc87.gif"
st, h, b1 = fetch(u, timeout=30)
print(" 1st:", st, len(b1), "md5", hashlib.md5(b1).hexdigest()[:12], h.get("Date"))
time.sleep(45)
st, h, b2 = fetch(u, timeout=30)
print(" 2nd:", st, len(b2), "md5", hashlib.md5(b2).hexdigest()[:12], h.get("Date"))
print(" same bytes:", b1 == b2)

print("\n== andorra gif freshness ==")
st, h, b = fetch("https://imgs.mobilitat.ad/prod/RotondaDamaGel.gif", timeout=30)
print(" gif:", st, h.get("Content-Type"), len(b), "lm=", h.get("Last-Modified"), "etag=", h.get("ETag"))
