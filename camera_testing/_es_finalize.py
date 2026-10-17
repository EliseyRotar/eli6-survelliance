# -*- coding: utf-8 -*-
"""Finalize inventory: drop 29 dead Andorra-border dupes, fix emap URL + eusk-127 typo."""
import json
import os
from collections import Counter

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
inv = json.load(open(os.path.join(ROOT, "_es_inventory.json"), encoding="utf-8"))
excluded = set(json.load(open(os.path.join(ROOT, "_es_overlap2.json"), encoding="utf-8"))["excluded"])

final = []
dropped_dup = 0
for e in inv:
    if e["key"] in excluded:
        continue
    if e["prefix"] == "cat" and "app.mobilitat.ad/gifs/" in e["image_url"]:
        dropped_dup += 1
        continue
    if e["key"] == "cat-5":
        e["image_url"] = e["image_url"].replace(" &#13;", "").strip()
        e["key"] = "cat-emap-cam01"
        e["notes"] += "; source=gencat-wfs (link=emap.terrassa.cat); rectified-url-trailing-entity"
    if e["key"] == "eusk-127":
        e["image_url"] = e["image_url"].replace("127 .jpg", "127.jpg")
        e["notes"] += "; source-url-had-space-typo (127 .jpg -> 127.jpg)"
    final.append(e)

print("dropped dead andorra-border dups:", dropped_dup)
print("final:", len(final), dict(Counter(e["prefix"] for e in final)))

# fold census results into entries
cen = json.load(open(os.path.join(ROOT, "_es_census.json"), encoding="utf-8"))["new"]
for e in final:
    v = cen.get(e["key"])
    if e["key"] == "cat-5":
        v = cen.get("cat-5") or cen.get("cat-emap-cam01")
    if v:
        e["http_status"] = str(v["status"]) if v["status"] is not None else ""
        e["census_lm"] = v.get("lm") or ""
        if v["status"] == 200:
            if e["prefix"] == "web":
                pass
            else:
                e["live_status"] = "live"
        elif v["status"] == 404:
            e["live_status"] = ""
            e["notes"] += "; image-404@2026-10-17"
        else:
            e["live_status"] = ""
            e["notes"] += "; img-host-unreachable-from-ingest-network@2026-10-17"
        if v.get("lm") and e["prefix"] == "dgt":
            e["notes"] += "; img_lm=" + v["lm"]

json.dump(final, open(os.path.join(ROOT, "_es_inventory_final.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print("live_status:", dict(Counter(e["live_status"] for e in final)))
print("http_status:", dict(Counter(e["http_status"] for e in final)))
print("non-200 entries:")
for e in final:
    if e["http_status"] != "200":
        print("   ", e["key"], e["http_status"], "|", e["image_url"][:80])
