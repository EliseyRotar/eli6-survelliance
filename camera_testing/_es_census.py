# -*- coding: utf-8 -*-
"""Session 47 census: liveness+poster-cache for new inventory, live-check for existing DGT rows."""
import json
import os
import re
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
CSV = r"C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv"
CACHE = os.path.join(ROOT, "_es_cache")
os.makedirs(CACHE, exist_ok=True)
import csv
csv.field_size_limit(10**7)

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}


def fetch_img(url, timeout, want_bytes=True):
    st = None
    ctype = lm = None
    body = b""
    for attempt in (0, 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                st = r.status
                ctype = r.headers.get("Content-Type", "")
                lm = r.headers.get("Last-Modified", "")
                if want_bytes:
                    body = r.read(6_000_000)
                else:
                    body = r.read(64_000)
            break
        except urllib.error.HTTPError as e:
            st = e.code
            ctype = e.headers.get("Content-Type", "") if e.headers else ""
            lm = e.headers.get("Last-Modified", "") if e.headers else ""
            break
        except Exception:
            if attempt == 0:
                time.sleep(1.5)
                continue
            st = None
    return st, ctype, lm, body


# ---------- load inventory (minus excluded) ----------
inv = json.load(open(os.path.join(ROOT, "_es_inventory.json"), encoding="utf-8"))
excluded = set(json.load(open(os.path.join(ROOT, "_es_overlap2.json"), encoding="utf-8"))["excluded"])
final = [e for e in inv if e["key"] not in excluded]
json.dump(final, open(os.path.join(ROOT, "_es_inventory_final.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("new entries to census:", len(final))

# ---------- existing DGT rows from CSV ----------
dgt_rows = []
with open(CSV, encoding="utf-8", newline="") as f:
    for r in csv.DictReader(f):
        for u in (r.get("live_stream_url") or "", r.get("url") or ""):
            m = re.search(r"camarasEtraffic/(\d+)\.jpg", u or "")
            if m and "dgt.es" in u:
                dgt_rows.append({"idx": r["idx"], "csv_id": r["csv_id"], "id": m.group(1), "url": u})
                break
print("existing DGT rows to live-check:", len(dgt_rows))

# ---------- run ----------
res = {"new": {}, "dgt_refresh": {}}
t0 = time.time()


def work_new(e):
    url = e["image_url"]
    timeout = 8 if e["prefix"] in ("eusk",) else 15
    st, ctype, lm, body = fetch_img(url, timeout, want_bytes=True)
    if st is None and url.startswith("https://"):
        st, ctype, lm, body = fetch_img(url.replace("https://", "http://"), timeout, want_bytes=True)
    safe = re.sub(r"[^\w.-]", "_", e["key"])
    cache_path = None
    if st == 200 and body:
        if not (ctype or "").lower().startswith("image"):
            pass
        p = os.path.join(CACHE, safe + ".img")
        with open(p, "wb") as fh:
            fh.write(body)
        cache_path = p
    return e["key"], {"status": st, "ctype": ctype, "lm": lm, "bytes": len(body), "cache": cache_path}


def work_dgt(row):
    st, ctype, lm, body = fetch_img(row["url"], 12, want_bytes=False)
    return row["idx"], {"csv_id": row["csv_id"], "id": row["id"], "status": st, "lm": lm}


with ThreadPoolExecutor(max_workers=8) as ex:
    futs = [ex.submit(work_new, e) for e in final]
    futs += [ex.submit(work_dgt, r) for r in dgt_rows]
    done = 0
    total = len(futs)
    for f in as_completed(futs):
        k, v = f.result()
        if isinstance(k, int) or (isinstance(k, str) and k.isdigit()):
            res["dgt_refresh"][k] = v
        else:
            res["new"][k] = v
        done += 1
        if done % 200 == 0:
            print(f"  {done}/{total} {time.time()-t0:.0f}s", flush=True)

json.dump(res, open(os.path.join(ROOT, "_es_census.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# summary
from collections import Counter
nst = Counter(str(v["status"]) for v in res["new"].values())
print("new entries status:", dict(nst))
bad = {k: v for k, v in res["new"].items() if v["status"] != 200}
print("new non-200:", len(bad))
for k, v in list(bad.items())[:20]:
    print("   ", k, v["status"], v["bytes"])
dst = Counter(str(v["status"]) for v in res["dgt_refresh"].values())
print("existing DGT status:", dict(dst))
dead = [v for v in res["dgt_refresh"].values() if v["status"] != 200]
print("existing DGT non-200:", len(dead))
for v in dead[:25]:
    print("   idx", v["csv_id"], "id", v["id"], "status", v["status"])
print("elapsed", round(time.time() - t0), "s")
