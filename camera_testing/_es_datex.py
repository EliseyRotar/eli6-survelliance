# -*- coding: utf-8 -*-
"""Session 47: full DATEX2 + live-feed probes on etraffic."""
import json
import re
import urllib.request
import urllib.error

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Referer": "https://etraffic.dgt.es/etrafficWEB/"}


def fetch(url, timeout=180, headers=None, cap=None):
    hh = dict(UA)
    if headers:
        hh.update(headers)
    req = urllib.request.Request(url, headers=hh)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            if cap:
                data = r.read(cap)
            else:
                data = r.read()
            return r.status, dict(r.headers), data
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read(4000)
    except Exception as e:
        return None, {}, str(e).encode()


print("== full DATEX2 v3.7 ==")
st, h, b = fetch("https://nap.dgt.es/datex2/v3/dgt/DevicePublication/camaras_datex2_v37.xml", timeout=300)
print("status", st, "bytes", len(b))
if st == 200 and len(b) > 10000:
    open(ROOT + r"\_es_datex2_v37.xml", "wb").write(b)
    # quick parse stats
    txt = b.decode("utf-8", "replace")
    print("head:", txt[:400].replace("\n", " "))
    print("cctvCamera occurrences:", len(re.findall(r"cctv", txt, re.I)))
    print("id occurrences:", len(re.findall(r'<id>', txt)))
else:
    print(b[:300])

print("\n== live-feed probes ==")
# image variants on camarasEtraffic (is it only .jpg?)
probes = [
    "https://etraffic.dgt.es/camarasEtraffic/176130.mjpg",
    "https://etraffic.dgt.es/camarasEtraffic/176130.mjpeg",
    "https://etraffic.dgt.es/camarasEtraffic/176130.ts",
    "https://etraffic.dgt.es/camarasEtraffic/176130.mp4",
    "https://etraffic.dgt.es/camarasEtraffic/176130.gif",
    "https://etraffic.dgt.es/camarasEtraffic/176130/",
    "https://etraffic.dgt.es/camarasEtraffic/176130/video",
    "https://etraffic.dgt.es/camarasEtraffic/stream/176130",
    "https://etraffic.dgt.es/camarasEtraffic/176130/playlist.m3u8",
    "https://etraffic.dgt.es/camarasEtraffic/176130/index.m3u8",
    "https://etraffic.dgt.es/camarasEtraffic/live/176130.m3u8",
    "https://etraffic.dgt.es/api/camaras/176130",
    "https://etraffic.dgt.es/api/video/176130",
    "https://etraffic.dgt.es/etrafficWEB/api/cache/getVideo",
    "https://etraffic.dgt.es/estaticosEtraffic/",
    "https://etraffic.dgt.es/camarasEtraffic/archive/176130/",
    "https://etraffic.dgt.es/hls/176130/index.m3u8",
]
for u in probes:
    st, h, b = fetch(u, timeout=15)
    ct = h.get("Content-Type", "")
    interesting = st in (200, 401, 403) and not (st == 200 and "text/html" in ct and len(b) < 2000)
    print(f"  {'>>' if interesting else '  '} {u} -> {st} {ct} len={len(b)}")
    if interesting and st == 200 and len(b) < 400 and "image" not in ct:
        print("      body:", b[:200])

print("\n== host headers / DNS ==")
import socket
for host in ["etraffic.dgt.es", "camarasEtraffic.dgt.es", "infocar.dgt.es", "nap.dgt.es", "www.dgt.es"]:
    try:
        ips = sorted({ai[4][0] for ai in socket.getaddrinfo(host, 443)})
        print(" ", host, "->", ips)
    except Exception as e:
        print(" ", host, "FAIL", e)
