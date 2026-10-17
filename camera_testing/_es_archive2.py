# -*- coding: utf-8 -*-
"""Session 47 retry: archived viewer + CDX (with backoff) + camarasdgt js."""
import json
import re
import time
import urllib.request
import urllib.parse
import urllib.error

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def fetch(url, timeout=60, tries=4):
    for i in range(tries):
        req = urllib.request.Request(url, headers=UA)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            data = e.read(4000)
            if e.code == 429 and i < tries - 1:
                time.sleep(12 * (i + 1))
                continue
            return e.code, dict(e.headers), data
        except Exception as e:
            if i < tries - 1:
                time.sleep(5)
                continue
            return None, {}, str(e).encode()


print("== camarasdgt js/api ==")
html = open(ROOT + r"\_es_camarasdgt_road.html", encoding="utf-8").read()
scripts = re.findall(r'<script[^>]*src=["\']([^"\']+)["\']', html, re.I)
print("script srcs:", scripts)
inline = re.findall(r"<script(?![^>]*src)[^>]*>(.*?)</script>", html, re.S | re.I)
print("inline scripts:", len(inline))
for s in inline:
    s2 = s.strip()
    if s2:
        print("  ---", s2[:300].replace("\n", " "))

# fetch its js
for src in scripts:
    if src.startswith("/"):
        src = "https://www.camarasdgt.es" + src
    if "js" in src.split("/")[-1] or "script" in src:
        st, h, b = fetch(src)
        print(f"js {src}: {st} {len(b)}")
        if st == 200:
            js = b.decode("utf-8", "replace")
            open(ROOT + r"\_es_camarasdgt.js", "w", encoding="utf-8").write(js)
            hits = re.findall(r'https?://[^"\'`\s]+', js)
            ext = sorted({x for x in hits if "camarasdgt" not in x and "w3.org" not in x and "schema" not in x})
            print("  external refs:", ext[:20])
            for kw in ["json", "api", "camara", ".jpg", "fetch(", "XMLHttpRequest"]:
                n = js.count(kw)
                if n:
                    print(f"  kw {kw}: {n}")

print("\n== CDX legacy image path ==")
for q in ["infocar.dgt.es/etraffic/data/camaras/*", "etraffic.dgt.es/camarasEtraffic/*", "infocar.dgt.es/etraffic/data/*"]:
    st, h, b = fetch("http://web.archive.org/cdx/search/cdx?url=" + urllib.parse.quote(q) + "&output=json&limit=40&collapse=urlkey&filter=statuscode:200", timeout=60)
    try:
        arr = json.loads(b.decode())
        print(f"Q {q}: {max(0, len(arr)-1)} rows")
        for row in arr[1:25]:
            print("  ", row[1], row[2])
    except Exception as e:
        print(q, "fail", st, b[:150])
    time.sleep(3)

print("\n== archived dgt.es viewer page ==")
st, h, b = fetch("http://web.archive.org/web/20260509223257/https://www.dgt.es/conoce-el-estado-del-trafico/camaras-de-trafico/?pag=2&prov=28&carr=A-2", timeout=90)
print("archive:", st, len(b))
if st == 200:
    txt = b.decode("utf-8", "replace")
    open(ROOT + r"\_es_arch_dgt_viewer.html", "w", encoding="utf-8", errors="replace").write(txt)
    imgs = sorted(set(re.findall(r'https?://[^"\'\s>]+(?:camaras?)[^"\'\s>]*\.jpg[^"\'\s>]*', txt, re.I)))
    print("cam imgs:", len(imgs))
    for x in imgs[:15]:
        print(" ", x)
    tags = [t for t in re.findall(r"<img[^>]*src=[\"']([^\"']+)[\"']", txt, re.I)
            if not re.search(r"logo|icon|banner", t, re.I)]
    print("img srcs:", len(tags))
    for t in tags[:12]:
        print(" ", t)
