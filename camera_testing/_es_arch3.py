# -*- coding: utf-8 -*-
"""Session 47: fetch archived camarasdgt listing pages -> image universe."""
import json
import re
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, parse_qs, unquote

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

arr = json.load(open(ROOT + r"\_es_cdx_camarasdgt.json", encoding="utf-8"))
rows = arr[1:]
# latest snapshot per url, only depth<=2 listing-ish + andorra/webcam subtree
latest = {}
for ts, urlkey, ts2, mime, status, digest, length, redirect, mimetype in (
        (r[1], r[2], r[1], r[3], r[4], r[5], r[6], r[7] if len(r) > 7 else "", r[8] if len(r) > 8 else "")
        for r in rows):
    pass
# simpler: rows are [urlkey, timestamp, original, mimetype, statuscode, digest, length]
for r in rows:
    url = r[2]
    segs = urlparse(url).path.strip("/").split("/")
    if len(segs) == 0 or (len(segs) >= 3 and segs[0] not in ("andorra", "webcam")):
        continue
    if url.lower().endswith((".css", ".js", ".png", ".ico", ".xml", ".txt")):
        continue
    prev = latest.get(url)
    if prev is None or r[1] > prev:
        latest[url] = r[1]
print("listing urls to fetch:", len(latest), flush=True)


def fetch(url, timeout=60, tries=3):
    for i in range(tries):
        req = urllib.request.Request(url, headers=UA)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read(400000)
        except urllib.error.HTTPError as e:
            if e.code == 429 and i < tries - 1:
                time.sleep(10 * (i + 1))
                continue
            return e.code, e.read(2000)
        except Exception:
            if i < tries - 1:
                time.sleep(4)
                continue
            return None, b""


results = {}
errs = 0
t0 = time.time()


def work(item):
    url, ts = item
    wb = f"https://web.archive.org/web/{ts}id_/{url}"
    st, b = fetch(wb)
    if st != 200:
        return url, None
    html = b.decode("utf-8", "replace")
    imgs = re.findall(r"<img[^>]*?src=[\"']([^\"']+)[\"'][^>]*?>", html, re.I)
    cam = [t for t in imgs if not re.search(r"favicon|logo|icon|banner|placeholder|loading\.gif|goog|adsby", t, re.I)]
    titles = re.findall(r'<img[^>]*title=[\"\']([^\"\']*)[\"\']', html, re.I)
    alts = re.findall(r'<img[^>]*alt=[\"\']([^\"\']*)[\"\']', html, re.I)
    return url, {"imgs": cam, "titles": titles, "alts": alts, "ts": ts}


with ThreadPoolExecutor(max_workers=4) as ex:
    futs = [ex.submit(work, it) for it in latest.items()]
    for i, f in enumerate(as_completed(futs), 1):
        u, rec = f.result()
        if rec:
            results[u] = rec
        else:
            errs += 1
        if i % 50 == 0:
            print(f"  {i}/{len(latest)} ok={len(results)} err={errs} {time.time()-t0:.0f}s", flush=True)

json.dump(results, open(ROOT + r"\_es_arch_listings.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("done:", len(results), "errs:", errs, f"{time.time()-t0:.0f}s", flush=True)

etraffic_ids = set()
external = {}
for u, rec in results.items():
    for img in rec["imgs"]:
        m = re.search(r"camarasEtraffic/(\d+)\.jpg", img)
        if m:
            etraffic_ids.add(m.group(1))
            continue
        # descargar_imagen.php?url=
        m = re.search(r"url=([^&\"']+)", img)
        if m and "camarasEtraffic" not in m.group(1):
            src = unquote(m.group(1))
            external.setdefault(src, set()).add(u)
            continue
        if re.search(r"\.(jpg|jpeg|png|gif|webp)(\?|$)", img, re.I):
            external.setdefault(img, set()).add(u)

prod = json.load(open(ROOT + r"\_es_camaras_etraffic.json", encoding="utf-8"))["camaras"]
known = {c["idCamara"] for c in prod}
known |= {"993", "168856", "176531", "176532", "176533", "176534", "176535", "176537",
          "178574", "181921", "181924", "18", "103", "1040"}
new_ids = sorted(etraffic_ids - known, key=int)
print("etraffic ids:", len(etraffic_ids), "NEW:", len(new_ids), new_ids[:80])
print("external:", len(external))
for k in sorted(external):
    print(" ", k, "| pages:", len(external[k]))
