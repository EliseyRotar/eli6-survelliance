# -*- coding: utf-8 -*-
import glob
import re

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
pat = re.compile(r"https?://[^\s'\")\\]+")
hits = set()
for p in glob.glob(ROOT + r"\_es_*.py"):
    try:
        s = open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        continue
    for u in pat.findall(s):
        if re.search(r"gencat|cantur|euskadi|trafikoa|mobilitat|vitoria|socrata", u):
            hits.add((p.split("\\")[-1], u))
for f, u in sorted(hits):
    print(f"{f}: {u}")
