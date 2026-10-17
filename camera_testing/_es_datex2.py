# -*- coding: utf-8 -*-
"""Session 47: parse DATEX2 DevicePublication + SPA fallback check + subdomains."""
import json
import re
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


print("== DATEX2 structure ==")
txt = open(ROOT + r"\_es_datex2_v37.xml", encoding="utf-8", errors="replace").read()
print("size:", len(txt))
# unique tags
tags = re.findall(r"<([A-Za-z0-9:_-]+)", txt)
from collections import Counter
c = Counter(tags)
print("top tags:", c.most_common(40))
# find camera-ish
for kw in ["camera", "cctv", "video", "image", "devicePublication", "deviceClass", "numberOfCameras"]:
    n = len(re.findall(kw, txt, re.I))
    print(f"  {kw}: {n}")
# sample device
m = re.search(r"<d2:devicePublication.{0,3000}?</d2:devicePublication>", txt, re.S)
if m:
    print("device sample:", m.group(0)[:2000])
else:
    # maybe generic
    m = re.search(r"<\w+:devicePublication.{0,2500}", txt, re.S)
    print("fallback sample:", (m.group(0) if m else txt[4000:7000])[:2500])

print("\n== SPA fallback bodies ==")
for u in ["https://etraffic.dgt.es/api/camaras/176130", "https://etraffic.dgt.es/hls/176130/index.m3u8"]:
    st, h, b = fetch(u)
    body = b.decode("utf-8", "replace")
    print(u, st, h.get("Content-Type"), len(b))
    print("  head:", body[:200].replace("\n", " "))

print("\n== hackertarget subdomains ==")
st, h, b = fetch("https://api.hackertarget.com/hostsearch/?q=dgt.es", timeout=60)
if st == 200 and not b.startswith(b"error"):
    txt2 = b.decode("utf-8", "replace")
    open(ROOT + r"\_es_sub_dgt_es.txt", "w", encoding="utf-8").write(txt2)
    subs = [l.split(",", 1) for l in txt2.splitlines() if "," in l]
    print("subs:", len(subs))
    for ip, host in subs:
        print(" ", host, ip)
else:
    print(b[:200])

print("\n== crt.sh ==")
st, h, b = fetch("https://crt.sh/?q=%25.dgt.es&output=json", timeout=60)
print("crt:", st, len(b))
if st == 200:
    try:
        arr = json.loads(b.decode())
        names = sorted({n for e in arr for n in e["name_value"].splitlines()})
        print("names:", len(names))
        for n in names:
            print(" ", n)
        open(ROOT + r"\_es_crt_dgt.json", "w", encoding="utf-8").write(json.dumps(arr))
    except Exception as e:
        print("parse fail", e, b[:200])
else:
    print(b[:200])
