# -*- coding: utf-8 -*-
"""Session 47: re-extract youtube embeds + labels from archived webcam pages."""
import json
import re
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def fetch(url, timeout=50, tries=2):
    for i in range(tries):
        req = urllib.request.Request(url, headers=UA)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read(300000)
        except urllib.error.HTTPError as e:
            if e.code == 429 and i < tries - 1:
                time.sleep(10)
                continue
            return e.code, e.read(2000)
        except Exception:
            if i < tries - 1:
                time.sleep(3)
                continue
            return None, b""


arr = json.load(open(ROOT + r"\_es_cdx_webcam.json", encoding="utf-8"))
rows = arr[1:]
latest = {}
for r in rows:
    url = r[2]
    if url.lower().endswith((".css", ".js", ".png", ".ico", ".xml", ".txt", ".jpg")):
        continue
    if url not in latest or r[1] > latest[url]:
        latest[url] = r[1]

# also reuse already-fetched pages (they store imgs only) -> refetch is needed for html; refetch all 77
print("pages:", len(latest))


def parse(html, url):
    rec = {"url": url}
    yt = sorted(set(re.findall(r"youtube\.com/embed/([\w-]{6,})", html)))
    yt += sorted(set(re.findall(r"youtube\.com/watch\?v=([\w-]{6,})", html)))
    rec["yt"] = yt
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S | re.I)
    if m:
        rec["h1"] = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip()
    m = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
    if m:
        rec["title"] = re.sub(r"\s+", " ", m.group(1)).strip()
    # info table cells (Provincia/Poblacion/Ubicacion row)
    tb = re.search(r"<th><strong>Provincia</strong></th>(.*?)</table>", html, re.S | re.I)
    if tb:
        cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", c)).strip()
                 for c in re.findall(r"<td>(.*?)</td>", tb.group(1), re.S)]
        rec["table"] = cells[:6]
    # external non-youtube images
    imgs = re.findall(r"<img[^>]*?src=[\"']([^\"']+)[\"'][^>]*?>", html, re.I)
    rec["imgs"] = [t for t in imgs if not re.search(r"favicon|logo|icon|banner|placeholder|loading\.gif|goog|adsby", t, re.I)]
    return rec


results = {}
errs = 0
t0 = time.time()


def work(item):
    url, ts = item
    st, b = fetch(f"https://web.archive.org/web/{ts}id_/{url}")
    if st != 200 or not b:
        return url, None
    return url, parse(b.decode("utf-8", "replace"), url)


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

json.dump(results, open(ROOT + r"\_es_webcam_yt.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
withyt = {u: r for u, r in results.items() if r["yt"]}
print("done:", len(results), "errs:", errs, "pages with youtube:", len(withyt))
yts = {}
for u, r in results.items():
    for y in r["yt"]:
        yts.setdefault(y, {"pages": [], "labels": []})
        yts[y]["pages"].append(u)
        if r.get("h1"):
            yts[y]["labels"].append(r["h1"])
print("unique youtube ids:", len(yts))
for y, v in list(yts.items())[:40]:
    print(" ", y, "|", (v["labels"][:1] or v["pages"][:1]))
json.dump(yts, open(ROOT + r"\_es_webcam_yt_ids.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
