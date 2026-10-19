# -*- coding: utf-8 -*-
"""Session 47o: DGT eTraffic re-census.

1. Re-POST prod getCamaras (base64+XOR-0x66) → diff vs prior 1,960-id
   inventory → new ids (probe liveness).
2. Re-probe the 21 rows that 404'd on 2026-10-17 (live_status='' with
   'image-404@2026-10-17' note) → revived?
"""
import base64
import csv
import json
import os
import re
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
CT = os.path.join(ROOT, "camera_testing")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
      "Referer": "https://etraffic.dgt.es/etrafficWEB/",
      "Content-Type": "application/json"}
STAMP = "2026-10-19"


def fetch(url, timeout=45, data=b"", method="POST"):
    req = urllib.request.Request(url, data=data, headers=UA, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read(2000)
    except Exception as e:
        return None, str(e).encode()


def ps_decode(raw):
    txt = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    b = base64.b64decode(txt)
    return bytes(x ^ 0x66 for x in b).decode("utf-8")


# ---- 1. prod census ----
st, raw = fetch("https://etraffic.dgt.es/etrafficWEB/api/cache/getCamaras")
print("getCamaras:", st, len(raw))
now_cams = []
if st == 200 and raw:
    d = json.loads(ps_decode(raw))
    now_cams = d.get("camaras", d if isinstance(d, list) else [])
    print("  cams now:", len(now_cams), "urlBase:", d.get("urlBase") if isinstance(d, dict) else "?")

prior = json.load(open(os.path.join(CT, "_es_camaras_etraffic.json"), encoding="utf-8"))["camaras"]
prior_ids = {c["idCamara"] for c in prior}
now_ids = {c["idCamara"] for c in now_cams}
new_ids = sorted(now_ids - prior_ids, key=int)
gone_ids = sorted(prior_ids - now_ids, key=int)
print("prior:", len(prior_ids), "new:", len(new_ids), new_ids[:60])
print("gone from API:", len(gone_ids), gone_ids[:60])

json.dump({"date": STAMP, "cams": now_cams},
          open(os.path.join(CT, "_es_camaras_etraffic_%s.json" % STAMP), "w", encoding="utf-8"),
          ensure_ascii=False)


def probe(cid):
    url = "https://etraffic.dgt.es/camarasEtraffic/%s.jpg" % cid
    req = urllib.request.Request(url, headers={k: v for k, v in UA.items() if k != "Content-Type"})
    try:
        with urllib.request.urlopen(req, timeout=18) as r:
            b = r.read(300000)
            ok = r.status == 200 and "image" in r.headers.get("Content-Type", "") and len(b) > 2000
            return cid, r.status, r.headers.get("Content-Type"), r.headers.get("Last-Modified"), len(b), ok
    except urllib.error.HTTPError as e:
        return cid, e.code, "", "", 0, False
    except Exception:
        return cid, 0, "", "", 0, False


# probe new ids
new_res = {}
if new_ids:
    print("\n-- probing %d new ids --" % len(new_ids))
    with ThreadPoolExecutor(max_workers=6) as ex:
        for f in as_completed([ex.submit(probe, c) for c in new_ids]):
            cid, code, ct, lm, n, ok = f.result()
            new_res[cid] = {"code": code, "ctype": ct, "lm": lm, "bytes": n, "live": ok}
            if ok:
                print("  NEW LIVE", cid, lm, n, flush=True)
            elif code != 404:
                print("  new odd", cid, code, ct, n, flush=True)

# ---- 2. dead-row re-probe ----
print("\n-- re-probing rows dead @2026-10-17 --")
dead = []
with open(os.path.join(ROOT, "controllable_Webcams.csv"), newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if "image-404@2026-10-17" in (r.get("notes") or ""):
            m = re.search(r"camarasEtraffic/(\d+)\.jpg", (r.get("live_stream_url") or "") + (r.get("url") or ""))
            if m:
                dead.append((r["csv_id"], m.group(1)))
print("dead dgt rows:", len(dead))
revived = {}
if dead:
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(probe, cid): csv_id for csv_id, cid in dead}
        for f in as_completed(futs):
            cid, code, ct, lm, n, ok = f.result()
            csv_id = futs[f]
            if ok:
                revived[cid] = {"csv_id": csv_id, "code": code, "ctype": ct, "lm": lm, "bytes": n}
                print("  REVIVED", csv_id, cid, lm, n, flush=True)
            else:
                print("  still dead", csv_id, cid, code, flush=True)

json.dump({"date": STAMP, "api_now": len(now_cams),
           "new": {k: v for k, v in new_res.items()},
           "revived": revived, "gone_from_api": gone_ids},
          open(os.path.join(CT, "_es_recensus_%s.json" % STAMP), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nSUMMARY api=%d new=%d (live %d) revived=%d gone=%d" % (
    len(now_cams), len(new_ids), sum(1 for v in new_res.values() if v["live"]),
    len(revived), len(gone_ids)))
