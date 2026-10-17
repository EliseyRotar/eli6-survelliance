# -*- coding: utf-8 -*-
"""Session 47: archived viewer content + camarasdgt js api + video CDX hunt."""
import json
import re
import urllib.request
import urllib.parse
import urllib.error

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read(4000)
    except Exception as e:
        return None, {}, str(e).encode()


print("== archived dgt.es viewer page ==")
u = "http://web.archive.org/web/20260509223257/https://www.dgt.es/conoce-el-estado-del-trafico/camaras-de-trafico/?pag=2&prov=28&carr=A-2"
st, h, b = fetch(u, timeout=90)
print("archive:", st, len(b))
if st == 200:
    html = b.decode("utf-8", "replace")
    open(ROOT + r"\_es_arch_dgt_viewer.html", "w", encoding="utf-8", errors="replace").write(html)
    imgs = sorted(set(re.findall(r'https?://[^"\'\s>]+camaras[^"\'\s>]*\.jpg[^"\'\s>]*', html, re.I)))
    print("cam imgs:", len(imgs))
    for x in imgs[:15]:
        print(" ", x)
    # any img tags
    tags = re.findall(r"<img[^>]*src=[\"']([^\"']+)[\"']", html, re.I)
    tags = [t for t in tags if "logo" not in t.lower() and "icon" not in t.lower()]
    print("img srcs:", len(tags), tags[:12])
    # look for camara rows
    rows = re.findall(r"camara[^>]{0,200}", html, re.I)
    print("camara mentions:", len(rows))
    for r in rows[:6]:
        print("  ", r[:180])

print("\n== archived infocar legacy image path ==")
for q in ["infocar.dgt.es/etraffic/data/camaras/*", "infocar.dgt.es/etraffic/data/*", "etraffic.dgt.es/camarasEtraffic/*"]:
    st, b = fetch("http://web.archive.org/cdx/search/cdx?url=" + urllib.parse.quote(q) + "&output=json&limit=30&collapse=urlkey&filter=statuscode:200", timeout=60)
    try:
        arr = json.loads(b.decode())
        print(f"Q {q}: {len(arr)-1} rows")
        for row in arr[1:20]:
            print("  ", row[1], row[2])
    except Exception as e:
        print(q, "fail", b[:150])

print("\n== camarasdgt js/api ==")
html = open(ROOT + r"\_es_camarasdgt_road.html", encoding="utf-8").read()
scripts = re.findall(r'<script[^>]*src=["\']([^"\']+)["\']', html, re.I)
print("script srcs:", scripts)
inline = re.findall(r"<script(?![^>]*src)[^>]*>(.*?)</script>", html, re.S | re.I)
for s in inline:
    s2 = s.strip()
    if s2 and ("fetch" in s2 or "ajax" in s2 or ".json" in s2 or "api" in s2.lower() or "camara" in s2.lower()):
        print("inline hit:", s2[:800])
        print("---")
