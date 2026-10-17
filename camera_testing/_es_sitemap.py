# -*- coding: utf-8 -*-
"""Session 47: camarasdgt sitemap + buscador + andorra cam."""
import json
import re
import urllib.request
import urllib.error

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def fetch(url, timeout=40):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read(4000)
    except Exception as e:
        return None, {}, str(e).encode()


print("== sitemap ==")
for u in ["https://www.camarasdgt.es/sitemap.xml", "https://www.camarasdgt.es/robots.txt"]:
    st, h, b = fetch(u)
    print(u, st, len(b))
    if st == 200:
        txt = b.decode("utf-8", "replace")
        print(txt[:1500])
        if "sitemap" in txt:
            open(ROOT + r"\_es_camarasdgt_sitemap_index.xml", "w", encoding="utf-8").write(txt)

print("\n== buscador ==")
st, h, b = fetch("https://www.camarasdgt.es/buscador-camaras-trafico.php")
print("buscador:", st, len(b))
if st == 200:
    html = b.decode("utf-8", "replace")
    open(ROOT + r"\_es_camarasdgt_buscador.html", "w", encoding="utf-8").write(html)
    ids = sorted(set(re.findall(r'camarasEtraffic/(\d+)\.jpg', html)), key=int)
    print("ids:", len(ids), ids[:50])
    # embedded option lists / selects
    sels = re.findall(r'<select[^>]*>.*?</select>', html, re.S)
    print("selects:", len(sels))
    for s in sels[:3]:
        opts = re.findall(r'<option[^>]*value="([^"]*)"[^>]*>([^<]*)', s)
        print("  opts n:", len(opts), opts[:15])

print("\n== andorra cam ==")
st, h, b = fetch("https://www.camarasdgt.es/andorra/cg-1/pk5-307-margineda-937metres/")
print("page:", st, len(b))
if st == 200:
    html = b.decode("utf-8", "replace")
    open(ROOT + r"\_es_camarasdgt_andorra.html", "w", encoding="utf-8").write(html)
    imgs = sorted(set(re.findall(r'https?://[^"\'\s>]+\.jpg[^"\'\s>]*', html, re.I)))
    print("jpgs:", imgs)
    m = re.search(r'</nav>(.*)</footer>', html, re.S)
    seg = m.group(1) if m else html
    print(re.sub(r"\s+", " ", seg)[:2500])
