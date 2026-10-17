# -*- coding: utf-8 -*-
"""Session 47: camarasdgt leaf pages - structure + id universe."""
import json
import re
import time
import urllib.request
import urllib.error

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read(4000)
    except Exception as e:
        return None, {}, str(e).encode()


st, h, b = fetch("https://www.camarasdgt.es/guadalajara/a-2/")
print("leaf:", st, len(b))
if st == 200:
    html = b.decode("utf-8", "replace")
    open(ROOT + r"\_es_camarasdgt_leaf.html", "w", encoding="utf-8").write(html)
    imgs = sorted(set(re.findall(r'https?://[^"\'\s>]+\.jpg[^"\'\s>]*', html, re.I)))
    print("jpgs:", len(imgs))
    for u in imgs[:20]:
        print(" ", u)
    # ids referenced anywhere
    ids = sorted(set(re.findall(r'(?:camaras|data/camaras|camarasEtraffic)/(\d+)\.jpg', html)))
    print("path-ids:", ids[:40], "n=", len(ids))
    # detail links
    links = sorted(set(re.findall(r'href="(https://www\.camarasdgt\.es/[^"]+)"', html)))
    print("links n:", len(links))
    for l in links[:30]:
        if not re.search(r'\.(css|js|png|ico|xml)$', l):
            print(" ", l)
    # any embed structure
    m = re.search(r'</nav>(.*)</footer>', html, re.S)
    seg = m.group(1) if m else ""
    print("\ncontent seg:", len(seg))
    # find first cam block
    cm = re.search(r'(?i)(camara|webcam).{0,900}', seg)
    if cm:
        print("first cam ctx:", re.sub(r"\s+", " ", cm.group(0))[:900])
