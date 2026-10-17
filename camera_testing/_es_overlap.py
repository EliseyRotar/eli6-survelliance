# -*- coding: utf-8 -*-
"""Find CSV rows matching inventory image/source urls -> exclusions."""
import csv
import json
import os

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
CSV = r"C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv"
csv.field_size_limit(10**7)

inv = json.load(open(os.path.join(ROOT, "_es_inventory.json"), encoding="utf-8"))
inv_by_img = {e["image_url"]: e for e in inv}

matches = []
with open(CSV, encoding="utf-8", newline="") as f:
    for r in csv.DictReader(f):
        u = (r.get("live_stream_url") or "") + "|" + (r.get("url") or "") + "|" + (r.get("notes") or "")
        for img, e in inv_by_img.items():
            if img in u:
                matches.append((e["key"], img, r["idx"], r["csv_id"], r["project_name"][:50], r["country"]))
                break
        else:
            # looser: watch ids / source id tokens
            pass

print("direct image-url matches:", len(matches))
for m in matches:
    print("  ", m)

# also search by distinctive tokens for yt/vitoria/andorra/cantur
tokens = ["hvsK8Fvz4rE", "ngOvyL2KbuA", "trafikoa.eus", "vitoria-gasteiz.org", "mobilitat.ad",
          "cantur.com", "sctidcam", "camarasEtraffic/187", "mct.gencat"]
hits = {t: [] for t in tokens}
with open(CSV, encoding="utf-8", newline="") as f:
    for r in csv.DictReader(f):
        u = (r.get("live_stream_url") or "") + "|" + (r.get("url") or "") + "|" + (r.get("notes") or "") + "|" + (r.get("geo_source") or "") + "|" + (r.get("host") or "")
        for t in tokens:
            if t in u:
                hits[t].append((r["idx"], r["csv_id"], (r["live_stream_url"] or r["url"])[:100], r["country"]))
print()
for t, v in hits.items():
    print(f"{t}: {len(v)}")
    for row in v[:6]:
        print("   ", row)
