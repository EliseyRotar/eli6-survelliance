# -*- coding: utf-8 -*-
"""Session 47f: extract YouTube embeds from camarasdgt.es /webcam/ wayback pages.

arch4 only regexed <img>; YT lives in iframes. Re-fetch the 77 /webcam/
snapshots (max timestamp per url from _es_cdx_camarasdgt.json), extract
video ids + iframe srcs + titles, dedupe vs CSV.
"""
import csv
import json
import os
import re
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
OUT = ROOT + r"\_es_arch5_webcam.json"
CDX = ROOT + r"\_es_cdx_camarasdgt.json"
CSV = r"C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv"

YT_ID = re.compile(r"(?:youtube\.com/(?:embed/|watch\?v=|shorts/)|youtu\.be/)([\w-]{6,})")
IFRAME = re.compile(r"<iframe[^>]*?src=[\"']([^\"']+)[\"']", re.I)

arr = json.load(open(CDX, encoding="utf-8"))
latest = {}
for r in arr[1:]:
    url = r[2]
    segs = urlparse(url).path.strip("/").split("/")
    if not segs or segs[0] != "webcam":
        continue
    if url.lower().endswith((".css", ".js", ".png", ".ico", ".xml", ".txt", ".jpg")):
        continue
    prev = latest.get(url)
    if prev is None or r[1] > prev:
        latest[url] = r[1]

results = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
todo = {u: ts for u, ts in latest.items() if u not in results}
print(f"webcam pages {len(latest)} done {len(results)} todo {len(todo)}", flush=True)


def fetch(url, timeout=50, tries=3):
    for i in range(tries):
        req = urllib.request.Request(url, headers=UA)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read(600000)
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and i < tries - 1:
                time.sleep(10 + i * 8)
                continue
            return e.code, b""
        except Exception:
            if i < tries - 1:
                time.sleep(4)
                continue
            return None, b""


def work(item):
    url, ts = item
    st, b = fetch(f"https://web.archive.org/web/{ts}id_/{url}")
    if st != 200 or not b:
        return url, None
    html = b.decode("utf-8", "replace")
    ids = sorted(set(YT_ID.findall(html)))
    frames = sorted(set(IFRAME.findall(html)))
    yt_frames = [f for f in frames if "youtu" in f]
    title = ""
    m = re.search(r"<title>([^<]*)</title>", html, re.I)
    if m:
        title = m.group(1).strip()
    if not (ids or yt_frames):
        return url, {"ids": [], "frames": [f for f in frames if not f.startswith("data:")][:8], "title": title, "ts": ts}
    return url, {"ids": ids, "frames": yt_frames[:8], "title": title, "ts": ts}


t0 = time.time()
errs = 0
with ThreadPoolExecutor(max_workers=5) as ex:
    futs = [ex.submit(work, it) for it in todo.items()]
    n = 0
    for f in as_completed(futs):
        u, rec = f.result()
        n += 1
        if rec:
            results[u] = rec
        else:
            errs += 1
        if n % 25 == 0:
            json.dump(results, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
            print(f"  prog {n}/{len(todo)} err={errs} {time.time()-t0:.0f}s", flush=True)

json.dump(results, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
print("DONE pages:", len(results), "errs:", errs, f"{time.time()-t0:.0f}s", flush=True)

# dedupe vs CSV
yt_ids_csv = set()
with open(CSV, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        for u in (r.get("live_stream_url") or "", r.get("url") or ""):
            for m in YT_ID.finditer(u):
                yt_ids_csv.add(m.group(1))
print("known yt ids in csv:", len(yt_ids_csv))

new = {}
for page, rec in results.items():
    for vid in rec.get("ids", []):
        if vid not in yt_ids_csv:
            new.setdefault(vid, set()).add(page)
print("NEW yt ids:", len(new))
for vid, pages in sorted(new.items()):
    print(" ", vid, "| e.g.", sorted(pages)[0], "| title:", (results[sorted(pages)[0]].get("title") or "")[:60])

any_frames = {}
for page, rec in results.items():
    for fr in rec.get("frames", []):
        if "youtu" not in fr:
            any_frames.setdefault(fr, set()).add(page)
nonyt = len([1 for page, rec in results.items() for fr in rec.get("frames", []) if "youtu" not in fr])
print("non-yt iframe srcs:", len(any_frames))
for fr in list(sorted(any_frames))[:15]:
    print("  frame:", fr[:120])
