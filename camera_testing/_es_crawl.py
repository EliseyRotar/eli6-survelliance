# -*- coding: utf-8 -*-
"""Session 47: crawl camarasdgt detail pages -> extract image src + labels."""
import json
import re
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
OUT = ROOT + r"\_es_camarasdgt_pages.json"

urls = json.load(open(ROOT + r"\_es_camarasdgt_urls.json", encoding="utf-8"))
targets = urls["detail"]
# include depth-4 too
allu = json.load(open(ROOT + r"\_es_camarasdgt_urls.json", encoding="utf-8"))
# depth-4 weren't saved; re-derive from sitemap
txt = open(ROOT + r"\_es_camarasdgt_sitemap_index.xml", encoding="utf-8").read()
locs = re.findall(r"<loc>(.*?)</loc>", txt)
from urllib.parse import urlparse
d4 = [u for u in locs if len(urlparse(u).path.strip("/").split("/")) == 4]
targets = targets + d4
print("targets:", len(targets))

results = {}
lock_ok = [0]
errors = [0]
t0 = time.time()


def grab(u, tries=3):
    for i in range(tries):
        req = urllib.request.Request(u, headers=UA)
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                if r.status == 200:
                    return r.read(300000)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 * (i + 1))
        except Exception:
            time.sleep(2 * (i + 1))
    return None


def work(u):
    b = grab(u)
    if b is None:
        return u, None
    html = b.decode("utf-8", "replace")
    rec = {"url": u}
    m = re.search(r"<img[^>]*src=\"([^\"]+)\"[^>]*>", html, re.I)
    # pick cam img: prefer non-icon
    imgs = re.findall(r"<img[^>]*?src=\"([^\"]+)\"[^>]*?>", html, re.I)
    cam = None
    for t in imgs:
        if re.search(r"favicon|logo|icon|banner|adsbygoogle|placeholder", t, re.I):
            continue
        cam = t
        break
    rec["img"] = cam
    # title from <b> Cámara Webcam instalada en ... or h1
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S | re.I)
    if m:
        rec["h1"] = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip()
    m = re.search(r"Cámara Webcam instalada en\s*(.{0,200}?)</b>", html, re.S | re.I)
    if m:
        rec["desc"] = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip()
    m = re.search(r'<img[^>]*title="([^"]*)"', html, re.I)
    if m:
        rec["img_title"] = m.group(1)
    # breadcrumb
    bc = re.findall(r'breadcrumb-item[^>]*>\s*([^<]{1,80})\s*<', html)
    rec["bc"] = [x.strip() for x in bc if x.strip() and x.strip() != "Active"]
    return u, rec


with ThreadPoolExecutor(max_workers=8) as ex:
    futs = {ex.submit(work, u): u for u in targets}
    for i, f in enumerate(as_completed(futs), 1):
        u, rec = f.result()
        if rec:
            results[u] = rec
            lock_ok[0] += 1
        else:
            errors[0] += 1
        if i % 250 == 0:
            print(f"  {i}/{len(targets)} ok={lock_ok[0]} err={errors[0]} {time.time()-t0:.0f}s", flush=True)

json.dump(results, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("done pages:", len(results), "errors:", errors[0], f"{time.time()-t0:.0f}s")

# extract image universe
etraffic_ids = set()
external = {}
noimg = 0
for u, rec in results.items():
    img = rec.get("img")
    if not img:
        noimg += 1
        continue
    m = re.search(r"camarasEtraffic/(\d+)\.jpg", img)
    if m:
        etraffic_ids.add(m.group(1))
    else:
        external.setdefault(img, []).append(u)
print("pages w/o img:", noimg)
print("unique etraffic ids in pages:", len(etraffic_ids))
print("external image urls:", len(external))
for k, v in list(external.items())[:40]:
    print("  ", k, "| pages:", len(v))
