# -*- coding: utf-8 -*-
"""Exact DGT id set already in CSV."""
import csv
import json
import re

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
csv.field_size_limit(10**7)
have = {}
n = 0
with open(ROOT + r"\controllable_Webcams.csv", encoding="utf-8", newline="") as f:
    for r in csv.DictReader(f):
        u = (r.get("live_stream_url") or "") + "|" + (r.get("url") or "")
        m = re.search(r"camarasEtraffic/(\d+)\.jpg|data/camaras/(\d+)\.jpg", u)
        if m and "dgt.es" in u:
            cid = m.group(1) or m.group(2)
            have[cid] = {"idx": r["idx"], "csv_id": r["csv_id"], "proj": r["project_name"],
                         "geo": r["geo_source"], "lat": r["lat"], "lon": r["lon"]}
            n += 1
print("rows with dgt image url:", n, "unique ids:", len(have))
json.dump(have, open(ROOT + r"\camera_testing\_es_dgt_already.json", "w"), indent=1)

# compare vs our inventory
prod = json.load(open(ROOT + r"\camera_testing\_es_camaras_etraffic.json", encoding="utf-8"))["camaras"]
prod_ids = {c["idCamara"] for c in prod}
ours = prod_ids | {"993", "168856", "176531", "176532", "176533", "176534", "176535",
                   "176537", "178574", "181921", "181924", "18", "103", "1040"}
missing = sorted(ours - set(have), key=int)
extra = sorted(set(have) - ours, key=int)
print("our inventory:", len(ours))
print("missing from csv (to ingest):", len(missing))
print("missing sample:", missing[:40])
print("in csv but not in our inventory:", len(extra))
print("extra sample:", extra[:40])
# prefixes of dgt rows
from collections import Counter
print("prefixes:", Counter(v["csv_id"].split("_")[0] for v in have.values()))
