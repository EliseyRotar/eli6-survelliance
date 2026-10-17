# -*- coding: utf-8 -*-
"""Session 47: resume archived listing crawl with incremental save."""
import json
import os
import re
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, unquote

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
OUT = ROOT + r"\_es_arch_listings.json"

arr = json.load(open(ROOT + r"\_es_cdx_camarasdgt.json", encoding="utf-8"))
rows = arr[1:]
latest = {}
for r in rows:
    url = r[2]
    segs = [s for s in urlparse(url).path.strip("/").split("/")]
    if not segs or segs == [""]:
        continue
    if len(segs) >= 3 and segs[0] not in ("andorra", "webcam"):
        continue
    if url.lower().endswith((".css", ".js", ".png", ".ico", ".xml", ".txt")):
        continue
    prev = latest.get(url)
    if prev is None or r[1] > prev:
        latest[url] = r[1]

results = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
todo = {u: ts for u, ts in latest.items() if u not in results}
print(f"total {len(latest)} done {len(results)} todo {len(todo)}", flush=True)


def fetch(url, timeout=50, tries=2):
    for i in range(tries):
        req = urllib.request.Request(url, headers=UA)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read(400000)
        except urllib.error.HTTPError as e:
            if e.code == 429 and i < tries - 1:
                time.sleep(8)
                continue
            return e.code, e.read(1500)
        except Exception:
            if i < tries - 1:
                time.sleep(3)
                continue
            return None, b""


def work(item):
    url, ts = item
    st, b = fetch(f"https://web.archive.org/web/{ts}id_/{url}")
    if st != 200 or not b:
        return url, None
    html = b.decode("utf-8", "replace")
    imgs = re.findall(r"<img[^>]*?src=[\"']([^\"']+)[\"'][^>]*?>", html, re.I)
    cam = [t for t in imgs if not re.search(r"favicon|logo|icon|banner|placeholder|loading\.gif|goog|adsby", t, re.I)]
    titles = re.findall(r'<img[^>]*title=[\"\']([^\"\']*)[\"\']', html, re.I)
    return url, {"imgs": cam, "titles": titles, "ts": ts}


t0 = time.time()
errs = 0
done_this_run = 0
with ThreadPoolExecutor(max_workers=5) as ex:
    futs = [ex.submit(work, it) for it in todo.items()]
    for f in as_completed(futs):
        u, rec = f.result()
        if rec:
            results[u] = rec
            done_this_run += 1
        else:
            errs += 1
        if (done_this_run + errs) % 40 == 0:
            json.dump(results, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
            print(f"  prog {done_this_run+errs}/{len(todo)} ok+={done_this_run} err={errs} total_ok={len(results)} {time.time()-t0:.0f}s", flush=True)

json.dump(results, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
print("DONE ok:", len(results), "errs this run:", errs, f"{time.time()-t0:.0f}s", flush=True)

etraffic_ids = set()
external = {}
for u, rec in results.items():
    for img in rec.get("imgs", []):
        m = re.search(r"camarasEtraffic/(\d+)\.jpg", img)
        if m:
            etraffic_ids.add(m.group(1))
            continue
        m = re.search(r"url=([^&\"']+)", img)
        if m:
            src = unquote(m.group(1))
            if "camarasEtraffic" in src:
                m2 = re.search(r"camarasEtraffic/(\d+)\.jpg", src)
                if m2:
                    etraffic_ids.add(m2.group(1))
                continue
            external.setdefault(src, set()).add(u)
            continue
        if re.search(r"\.(jpg|jpeg|png|gif|webp)(\?|$)", img, re.I):
            external.setdefault(img, set()).add(u)

prod = json.load(open(ROOT + r"\_es_camaras_etraffic.json", encoding="utf-8"))["camaras"]
known = {c["idCamara"] for c in prod}
known |= {"993", "168856", "176531", "176532", "176533", "176534", "176535", "176537",
          "178574", "181921", "181924", "18", "103", "1040"}
new_ids = sorted(etraffic_ids - known, key=int)
print("etraffic ids:", len(etraffic_ids), "NEW:", len(new_ids), new_ids)
print("external:", len(external))
for k in sorted(external):
    print(" ", k, "| n:", len(external[k]), "| e.g.", list(external[k])[0])
