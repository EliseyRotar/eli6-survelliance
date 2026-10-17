# -*- coding: utf-8 -*-
"""Find still-garbled source-matched rows (no inv entry) + pending geocodes."""
import csv
import re
from collections import Counter

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
csv.field_size_limit(10**7)
rest = []
pat = re.compile(r" · ")
with open(ROOT + r"\controllable_Webcams.csv", encoding="utf-8", newline="") as f:
    for r in csv.DictReader(f):
        if "rectified-20261017" in (r["notes"] or ""):
            continue
        u = (r.get("live_stream_url") or "") + " " + (r.get("url") or "")
        src = None
        if "/static/files/tr/camaras/" in u:
            src = "eusk"
        elif "mct.gencat" in u or "sctidcam=" in u:
            src = "cat"
        elif "imgs.mobilitat.ad" in u:
            src = "ando"
        if src and pat.search(r["project_name"] or ""):
            m = re.search(r"camaras/(\d+)\s*\.jpg", u) or re.search(
                r"sctidcam=([\w.-]+?)(?:\.gif|\.jpg)?(?:&|\s|$)", u) or re.search(
                r"TransitCamera\?nom=([\w.-]+?)(?:\.gif|\.jpg)?(?:&|\s|$)", u) or \
                re.search(r"prod/([\w.-]+)\.gif", u)
            rest.append((src, r["csv_id"], m.group(1) if m else "?",
                         r["project_name"][:52], r["country"], r["region"][:22], r["lat"], r["lon"]))
print("still-garbled source-matched rows:", len(rest))
print("by src:", dict(Counter(x[0] for x in rest)))
for x in rest[:40]:
    print("  ", x)
