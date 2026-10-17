# -*- coding: utf-8 -*-
"""Session 47: infra sweep + pre-env + estaticos listing."""
import json
import re
import urllib.request
import urllib.error
import socket

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read(200000)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read(4000)
    except Exception as e:
        return None, {}, str(e).encode()


print("== estaticos listing ==")
st, h, b = fetch("https://etraffic.dgt.es/estaticosEtraffic/")
print(st, h.get("Content-Type"), len(b))
print(b[:1500].decode("utf-8", "replace"))

print("\n== pre env ==")
for u in [
    "https://etraffic-pre.dgt.es/etrafficWEB/",
    "https://etraffic-pre.dgt.es/etrafficWEB/api/cache/getCamaras",
]:
    if "getCamaras" in u:
        req = urllib.request.Request(u, data=b"", headers={**UA, "Content-Type": "application/json", "Referer": "https://etraffic-pre.dgt.es/"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                b = r.read()
                print(u, r.status, len(b))
                if len(b) < 500:
                    print(" body:", b[:300])
                else:
                    open(ROOT + r"\_es_pre_getCamaras.raw", "wb").write(b)
        except Exception as e:
            print(u, "ERR", e)
    else:
        st, h, b = fetch(u)
        print(u, st, h.get("Content-Type"), len(b))

print("\n== interesting DGT hosts probe ==")
for host in ["gis.dgt.es", "srvgis.dgt.es", "infocar.dgt.es", "apl.dgt.es", "stars.dgt.es", "stre.dgt.es", "dit.dgt.es"]:
    for path in ["/", "/camaras", "/video", "/cctv", "/axis-cgi/mjpg/video.cgi", "/cgi-bin/mjpg/video.cgi"]:
        st, h, b = fetch(f"https://{host}{path}", timeout=10)
        ct = h.get("Content-Type", "")
        marker = ""
        if st == 200 and ("image" in ct or "video" in ct or "mjpeg" in ct):
            marker = " <== STREAM"
        if st not in (200, 404, 403, 301, 302, None) or marker:
            print(f"  {host}{path} -> {st} {ct} len={len(b)}{marker}")
    # just host root status
    st, h, b = fetch(f"https://{host}/", timeout=10)
    print(f"  root {host} -> {st} {h.get('Content-Type')} len={len(b)} title=", end="")
    t = re.search(rb"<title>(.*?)</title>", b, re.S | re.I)
    print(t.group(1)[:80] if t else b[:80])

print("\n== InternetDB sweep of DGT infra (195.53.65.x) ==")
sample_ips = ["195.53.65.130", "195.53.65.131", "195.53.65.134", "195.53.65.139",
              "195.53.65.144", "195.53.65.145", "195.53.65.146", "195.53.65.148",
              "195.53.65.149", "195.53.65.151", "195.53.65.153", "212.128.100.139",
              "212.128.100.158", "212.128.100.240", "212.128.100.246"]
port_hits = []
for ip in sample_ips:
    st, h, b = fetch(f"https://internetdb.shodan.io/{ip}", timeout=12)
    try:
        d = json.loads(b.decode())
    except Exception:
        print("  fail", ip)
        continue
    ports = d.get("ports", [])
    flag = ""
    if any(p in ports for p in (554, 8000, 8080, 8554, 1935, 5000, 5001, 8883, 10000)):
        flag = " <== STREAMY"
        port_hits.append({"ip": ip, "ports": ports, "hosts": d.get("hostnames")})
    print(f"  {ip} ports={ports}{flag}")

print("\nport_hits:", port_hits)
