# -*- coding: utf-8 -*-
"""CSV vocab census."""
import csv
from collections import Counter

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
csv.field_size_limit(10**7)
types = Counter()
cats = Counter()
vis = Counter()
ls = Counter()
lp = Counter()
geo = Counter()
n = 0
with open(ROOT + r"\controllable_Webcams.csv", encoding="utf-8", newline="") as f:
    for r in csv.DictReader(f):
        n += 1
        types[r.get("type", "")] += 1
        cats[r.get("category", "")] += 1
        vis[r.get("visibility", "")] += 1
        ls[r.get("live_status", "")] += 1
        lp[r.get("location_precision", "")] += 1
        geo[r.get("geo_source", "")] += 1
print("rows:", n)
print("type:", dict(types.most_common()))
print("category:", dict(cats.most_common()))
print("visibility:", dict(vis.most_common()))
print("live_status:", dict(ls.most_common()))
print("location_precision:", dict(lp.most_common(15)))
print("geo_source:", dict(geo.most_common(15)))
