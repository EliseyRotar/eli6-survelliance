# -*- coding: utf-8 -*-
"""Session 47: legacy-infocar id liveness + external host inventory."""
import json
import re
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import unquote

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Referer": "https://etraffic.dgt.es/etrafficWEB/"}

arch = json.load(open(ROOT + r"\_es_arch_listings.json", encoding="utf-8"))
prod = json.load(open(ROOT + r"\_es_camaras_etraffic.json", encoding="utf-8"))["camaras"]
known = {c["idCamara"] for c in prod}
known |= {"993", "168856", "176531", "176532", "176533", "176534", "176535", "176537",
          "178574", "181921", "181924", "18", "103", "1040"}

legacy_ids = set()
external = set()
for u, rec in arch.items():
    for img in rec.get("imgs", []):
        m = re.search(r"camarasEtraffic/(\d+)\.jpg", img)
        if m:
            legacy_ids.add(m.group(1))
            continue
        m = re.search(r"data/camaras/(\d+)\.jpg", img)
        if m:
            legacy_ids.add(m.group(1))
            continue
        m = re.search(r"url=([^&\"']+)", img)
        if m:
            src = unquote(m.group(1))
            m2 = re.search(r"(?:camarasEtraffic|data/camaras)/(\d+)\.jpg", src)
            if m2:
                legacy_ids.add(m2.group(1))
            else:
                external.add(src)
            continue
        if re.search(r"\.(jpg|jpeg|png|gif|webp)(\?|$)", img, re.I):
            external.add(img)

unknown = sorted(legacy_ids - known, key=int)
print("legacy/known ids harvested:", len(legacy_ids), "unknown:", len(unknown))
print(unknown)

# liveness on current host
def test(cid):
    req = urllib.request.Request(f"https://etraffic.dgt.es/camarasEtraffic/{cid}.jpg", headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            b = r.read(200000)
            if r.status == 200 and "image" in r.headers.get("Content-Type", "") and len(b) > 2000:
                return cid, r.headers.get("Last-Modified"), len(b)
            return cid, None, 0
    except urllib.error.HTTPError:
        return cid, None, 0
    except Exception:
        return cid, None, -1


alive = {}
with ThreadPoolExecutor(max_workers=6) as ex:
    for f in as_completed([ex.submit(test, c) for c in unknown]):
        cid, lm, n = f.result()
        if lm:
            alive[cid] = lm
            print("  ALIVE", cid, lm, n, flush=True)
print("alive new:", len(alive))
json.dump({"alive": alive, "unknown": unknown, "external": sorted(external)},
          open(ROOT + r"\_es_new_ids.json", "w"), indent=1)
print("external hosts:")
from urllib.parse import urlparse
from collections import Counter
print(Counter(urlparse(x).netloc for x in external))
