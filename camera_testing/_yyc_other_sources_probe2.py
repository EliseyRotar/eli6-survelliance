# -*- coding: utf-8 -*-
"""Session 48f2: deep probe AB511 history endpoints + trafficcalgary API +
IEM archive dirs (sources that may support slideshow loops)."""
import os
import re
import subprocess

TEMP = os.environ["TEMP"]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def fetch(url, out_name, timeout=30):
    op = os.path.join(TEMP, out_name)
    p = subprocess.run(["curl", "-sL", "-A", UA, "--max-time", str(timeout),
                        "-o", op, "-w", "%{http_code}|%{content_type}|%{size_download}", url],
                       capture_output=True, text=True, timeout=timeout + 10)
    body = b""
    if os.path.exists(op):
        with open(op, "rb") as f:
            body = f.read()
    return p.stdout.strip(), body


# ---------- AB511 ----------
print("=== AB511 homepage JS ===")
meta, body = fetch("https://511.alberta.ca/", "ab511_home.html")
print("home:", meta)
text = body.decode("utf-8", "replace")
js_files = set(re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', text)) | \
           set(re.findall(r'url:\s*["\']([^"\']+\.js[^"\']*)["\']', text))
js_files = [j for j in js_files if "googlesyndication" not in j and "gtm" not in j and "analytics" not in j]
print("js candidates:", len(js_files))
for j in sorted(js_files):
    print("  ", j[:140])

# grep html for Cctv / image endpoints
for kw in ("Cctv", "cctv", "history", "ImageHistory", "previous", "timeSlider"):
    hits = re.findall(r'["\']([^"\']*%s[^"\']*)["\']' % kw, text)
    for h in sorted(set(hits))[:6]:
        print("  [%s] %s" % (kw, h[:150]))

# probe plausible history URL variants on Cctv id
cid = "138975"
variants = [
    "https://511.alberta.ca/map/Cctv/%s" % cid,
    "https://511.alberta.ca/map/Cctv/%s/1" % cid,
    "https://511.alberta.ca/map/CctvImg/%s" % cid,
    "https://511.alberta.ca/map/Cctv/%s?index=1" % cid,
    "https://511.alberta.ca/map/Cctv/%s?frame=1" % cid,
    "https://511.alberta.ca/api/cctv/%s/history" % cid,
    "https://511.alberta.ca/map/api/Cctv/%s/History" % cid,
]
for v in variants:
    m, b = fetch(v, "v.bin")
    print("  %-70s -> %s head=%r" % (v[:70], m[:40], b[:8]))

# ---------- trafficcalgary ----------
print("\n=== trafficcalgary.ca API ===")
m2, b2 = fetch("https://trafficcalgary.ca/", "tcag2.html")
t2 = b2.decode("utf-8", "replace")
# all script srcs (relative too)
sc = set(re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', t2))
print("script srcs:", sorted(sc)[:20])
# fetch/axios/xhr calls inline
for m in re.finditer(r'(?:fetch|axios|XMLHttpRequest|\.get|open)\s*\(\s*[`"\']([^`"\']+)', t2):
    print("  call:", m.group(1)[:150])
# data-* attrs mentioning api/json
for m in re.finditer(r'data-[a-z-]+=["\']([^"\']*(?:api|json|feed|cam)[^"\']*)["\']', t2, re.I):
    print("  data:", m.group(1)[:150])

# ---------- IEM archive ----------
print("\n=== IEM/KCCI archive dirs ===")
d = "https://mesonet.agron.iastate.edu/archive/data/2026/07/22/camera/KCCI-036/"
m3, b3 = fetch(d, "iem_dir.html")
print("dir:", m3)
t3 = b3.decode("utf-8", "replace")
links = re.findall(r'href=["\']([^"\']+)["\']', t3)
jpgs = [l for l in links if re.search(r'\.(jpg|png)$', l)]
print("image links:", len(jpgs), jpgs[:5])
# granularity: any sub-minute dirs?
dirs = [l for l in links if l.endswith('/')]
print("subdirs:", dirs[:10])
