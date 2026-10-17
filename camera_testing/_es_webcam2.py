# -*- coding: utf-8 -*-
"""Session 47: decode getPMVs/getFilteredData + fetch archived webcam leaf pages."""
import base64
import json
import re
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Referer": "https://etraffic.dgt.es/etrafficWEB/"}


def fetch(url, timeout=60, data=None, method=None, headers=None, tries=3):
    hh = dict(UA)
    if headers:
        hh.update(headers)
    for i in range(tries):
        req = urllib.request.Request(url, data=data, headers=hh, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and i < tries - 1:
                time.sleep(10)
                continue
            return e.code, dict(e.headers), e.read(3000)
        except Exception:
            if i < tries - 1:
                time.sleep(4)
                continue
            return None, {}, b""


def ps_decode(raw):
    txt = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    b = base64.b64decode(txt)
    return bytes(x ^ 0x66 for x in b).decode("utf-8")


print("== getPMVs ==")
st, h, b = fetch("https://etraffic.dgt.es/etrafficWEB/api/cache/getPMVs", data=b"", method="POST", timeout=60)
print("pmvs:", st, len(b))
if st == 200:
    try:
        d = json.loads(ps_decode(b))
        open(ROOT + r"\_es_getPMVs.json", "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False))
        print(" keys:", list(d.keys()))
        for k, v in d.items():
            if isinstance(v, list):
                print(f"  {k}: n={len(v)}", json.dumps(v[0], ensure_ascii=False)[:300] if v else "")
    except Exception as e:
        print(" fail:", e, b[:80])

print("\n== getFilteredData (proper CT) ==")
st, h, b = fetch("https://etraffic.dgt.es/etrafficWEB/api/cache/getFilteredData",
                 data=b"{}", method="POST",
                 headers={"Content-Type": "application/json; charset=UTF-8"}, timeout=60)
print("filtered:", st, len(b))
if st == 200 and b:
    try:
        d = json.loads(ps_decode(b))
        open(ROOT + r"\_es_getFilteredData.json", "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False))
        print(" keys:", list(d.keys()))
        for k, v in d.items():
            if isinstance(v, list):
                print(f"  {k}: n={len(v)}", json.dumps(v[0], ensure_ascii=False)[:300] if v else "")
    except Exception as e:
        print(" fail:", e, b[:80])

print("\n== archived webcam pages ==")
arr = json.load(open(ROOT + r"\_es_cdx_webcam.json", encoding="utf-8"))
rows = arr[1:]
latest = {}
for r in rows:
    url = r[2]
    if url.lower().endswith((".css", ".js", ".png", ".ico", ".xml", ".txt", ".jpg")):
        continue
    if url not in latest or r[1] > latest[url]:
        latest[url] = r[1]
print("to fetch:", len(latest))


def work(item):
    url, ts = item
    st, h, b = fetch(f"https://web.archive.org/web/{ts}id_/{url}", timeout=50, tries=2)
    if st != 200 or not b:
        return url, None
    html = b.decode("utf-8", "replace")
    imgs = re.findall(r"<img[^>]*?src=[\"']([^\"']+)[\"'][^>]*?>", html, re.I)
    cam = [t for t in imgs if not re.search(r"favicon|logo|icon|banner|placeholder|loading\.gif|goog|adsby", t, re.I)]
    titles = re.findall(r'<img[^>]*title=[\"\']([^\"\']*)[\"\']', html, re.I)
    return url, {"imgs": cam, "titles": titles, "ts": ts}


results = json.load(open(ROOT + r"\_es_arch_webcam.json", encoding="utf-8")) if False else {}
errs = 0
t0 = time.time()
with ThreadPoolExecutor(max_workers=4) as ex:
    futs = [ex.submit(work, it) for it in latest.items()]
    for i, f in enumerate(as_completed(futs), 1):
        u, rec = f.result()
        if rec:
            results[u] = rec
        else:
            errs += 1
        if i % 30 == 0:
            print(f"  {i}/{len(latest)} ok={len(results)} err={errs} {time.time()-t0:.0f}s", flush=True)

json.dump(results, open(ROOT + r"\_es_arch_webcam.json", "w", encoding="utf-8"), ensure_ascii=False)
print("done:", len(results), "errs:", errs, f"{time.time()-t0:.0f}s")

from urllib.parse import urlparse, unquote
from collections import Counter
hosts = Counter()
urls_ext = set()
for u, rec in results.items():
    for img in rec["imgs"]:
        if "camarasEtraffic" in img or "data/camaras" in img:
            hosts["dgt"] += 1
            continue
        m = re.search(r"url=([^&\"']+)", img)
        if m:
            src = unquote(m.group(1))
        else:
            src = img
        if re.search(r"\.(jpg|jpeg|png|gif|webp)(\?|$)", src, re.I):
            urls_ext.add(src)
            hosts[urlparse(src).netloc] += 1
print("hosts:", dict(hosts))
print("external urls:", len(urls_ext))
for x in sorted(urls_ext)[:60]:
    print(" ", x)
