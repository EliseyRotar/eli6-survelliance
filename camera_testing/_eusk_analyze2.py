# -*- coding: utf-8 -*-
import csv
import re
from collections import defaultdict

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
CSV = ROOT + r"\controllable_Webcams.csv"

HOSTS = ("trafikoa", "bizkaimove", "bilbao.eus", "vitoria-gasteiz")


def cam_id(url):
    m = re.search(r"camaras/(\d+)\s*\.jpg", url, re.I)
    if m:
        return "trk" + m.group(1)
    m = re.search(r"/cam(\d+)\.jpg", url, re.I)
    if m:
        return "bm" + m.group(1)
    m = re.search(r"codec(\d+)", url, re.I)
    if m:
        return "blb" + m.group(1)
    m = re.search(r"[?&]id=(\w+)", url, re.I)
    if m:
        return "vgz" + m.group(1)
    return None


by_host = defaultdict(list)
by_id = defaultdict(list)
with open(CSV, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        u = ((r.get("live_stream_url") or "") + " " + (r.get("url") or "")).lower()
        if not any(h in u for h in HOSTS):
            continue
        k = cam_id((r.get("live_stream_url") or "") + " " + (r.get("url") or ""))
        by_host[
            "trafikoa" if "trafikoa" in u else "bizkaimove" if "bizkaimove" in u else "bilbao" if "bilbao.eus" in u else "vitoria"
        ].append(r)
        if k:
            by_id[k].append(r)

print("host-scoped csv rows:", {k: len(v) for k, v in by_host.items()})
print("host-scoped camids:", len(by_id))
for h in ("bilbao", "vitoria", "bizkaimove"):
    rs = by_host[h]
    for r in rs[:3]:
        print(f"  {h} sample:", r["csv_id"], "|", (r["project_name"] or "")[:45], "|", (r["live_stream_url"] or r["url"] or "")[:95], "| live:", r["live_status"])
junk = [r["csv_id"] for h in by_host for r in by_host[h] if "Apps" in (r.get("project_name") or "")]
print("junk-titled among host-scoped:", len(junk))
nocoord = [r["csv_id"] for h in by_host for r in by_host[h] if not (r.get("lat") and r.get("lon"))]
print("missing coords:", len(nocoord))
