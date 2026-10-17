# -*- coding: utf-8 -*-
"""Session 47: full CDX id harvest + liveness of unknown ids + viewer/camarasdgt inspection."""
import json
import re
import time
import urllib.request
import urllib.parse
import urllib.error

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
PROD_BASE = "https://etraffic.dgt.es/camarasEtraffic/"


def fetch(url, timeout=90, tries=4, headers=None):
    hh = dict(UA)
    if headers:
        hh.update(headers)
    for i in range(tries):
        req = urllib.request.Request(url, headers=hh)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            data = e.read(4000)
            if e.code == 429 and i < tries - 1:
                time.sleep(12 * (i + 1))
                continue
            return e.code, dict(e.headers), data
        except Exception:
            if i < tries - 1:
                time.sleep(4)
                continue
            return None, {}, b""


# 1) full CDX harvests
print("== full CDX harvest ==")
ids_legacy = set()
ids_etraffic = set()
for q, bucket in [("infocar.dgt.es/etraffic/data/camaras/*", ids_legacy),
                  ("etraffic.dgt.es/camarasEtraffic/*", ids_etraffic)]:
    # paged
    page = ""
    total = 0
    while True:
        u = ("http://web.archive.org/cdx/search/cdx?url=" + urllib.parse.quote(q) +
             "&output=json&collapse=urlkey&filter=statuscode:200&limit=2000" + page)
        st, h, b = fetch(u, timeout=120)
        try:
            arr = json.loads(b.decode())
        except Exception:
            print("  cdx fail", st, b[:120])
            break
        rows = arr[1:]
        for row in rows:
            key = row[2]
            m = re.search(r"/camaras/(\d+)\.jpg|/camarasEtraffic/(\d+)\.jpg", key)
            if m:
                bucket.add(m.group(1) or m.group(2))
        total += len(rows)
        if len(rows) < 2000:
            break
        page = "&showResumeKey=true&resumeKey=" + urllib.parse.quote(arr[-1][-1]) if arr else ""
        time.sleep(2)
    print(f"  {q}: rows~{total} unique ids={len(bucket)}")

# 2) known inventory
prod = json.load(open(ROOT + r"\_es_camaras_etraffic.json", encoding="utf-8"))["camaras"]
known = {c["idCamara"] for c in prod}
known |= {"993", "168856", "176531", "176532", "176533", "176534", "176535", "176537", "178574", "181921", "181924"}
all_hist = ids_legacy | ids_etraffic
unknown = sorted(all_hist - known, key=lambda x: int(x))
print("\nknown:", len(known), "historical:", len(all_hist), "unknown:", len(unknown))
print("unknown sample:", unknown[:60])

# 3) liveness test unknown ids on live host (HEAD-ish GET)
print("\n== unknown id liveness ==")
alive = []
checked = 0
for cid in unknown:
    st, h, b = fetch(PROD_BASE + cid + ".jpg", timeout=15, tries=2)
    checked += 1
    if st == 200 and "image" in h.get("Content-Type", "") and len(b) > 2000:
        alive.append(cid)
        print("  ALIVE", cid, h.get("Last-Modified"), len(b))
    if checked % 50 == 0:
        print("  ...checked", checked)
print("alive unknown:", len(alive), alive)
json.dump({"alive": alive, "unknown_total": len(unknown), "legacy_ids": sorted(ids_legacy, key=int),
           "etraffic_ids": sorted(ids_etraffic, key=int)},
          open(ROOT + r"\_es_hist_liveness.json", "w"), indent=1)

# 4) archived viewer inspection
print("\n== archived viewer inspection ==")
txt = open(ROOT + r"\_es_arch_dgt_viewer.html", encoding="utf-8", errors="replace").read()
for kw in ["templ_imageSrc", "camaras.json", "camarasEtraffic", "data/camaras", "infocar"]:
    for m in re.finditer(re.escape(kw), txt):
        s = max(0, m.start() - 200)
        print(f"  [{kw}]", txt[s:m.start() + 250].replace("\n", " ")[:450])
        break
srcs = re.findall(r'<script[^>]*src=["\']([^"\']+)["\']', txt, re.I)
print("script srcs:", srcs[:15])

# 5) camarasdgt road structure
print("\n== camarasdgt road structure ==")
rhtml = open(ROOT + r"\_es_camarasdgt_road.html", encoding="utf-8").read()
# find main content after nav
m = re.search(r'<main.*?</main>', rhtml, re.S | re.I)
if not m:
    m = re.search(r'<div id="content".*?</body>', rhtml, re.S | re.I)
seg = m.group(0) if m else rhtml
print("segment len:", len(seg))
# strip nav
print(seg[:3000])
