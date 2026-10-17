# -*- coding: utf-8 -*-
"""Session 46: sweep all bcferries current-conditions route pages for cams."""
import re
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

with open(ROOT + r"\_bcf_current_conditions.html", encoding="utf-8") as f:
    cc = f.read()
links = sorted(set(re.findall(r'href="(/current-conditions/([A-Z]{3})-([A-Z]{3}))"', cc)))
print("route pages:", len(links))


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def probe(item):
    path, a, b = item
    url = "https://www.bcferries.com" + path
    try:
        html = fetch(url)
    except Exception as e:
        return {"path": path, "error": str(e)}
    cams = sorted(set(re.findall(r'https://ccimg\.bcferries\.com/[^"\'\s>]+', html)))
    # also catch relative img srcs and terminal webcam blocks
    rel_cams = sorted(set(re.findall(r'src="(https?://[^"]*cam[^"]*\.(?:jpg|jpeg|png)[^"]*)"', html, re.I)))
    # any mention of "webcam"
    has_webcam_word = "webcam" in html.lower()
    return {
        "path": path,
        "route": f"{a}-{b}",
        "ccimg": cams,
        "cam_imgs": rel_cams,
        "has_webcam": has_webcam_word,
        "bytes": len(html),
    }


results = []
with ThreadPoolExecutor(max_workers=8) as ex:
    futs = [ex.submit(probe, it) for it in links]
    for i, fut in enumerate(as_completed(futs), 1):
        results.append(fut.result())
        if i % 20 == 0:
            print(f"  {i}/{len(links)}")

results.sort(key=lambda r: r["path"])
with_cams = [r for r in results if r.get("ccimg") or r.get("cam_imgs")]
with_word = [r for r in results if r.get("has_webcam")]
print("pages with ccimg:", len(with_cams))
print("pages mentioning webcam:", len(with_word))
for r in with_cams:
    print(r["route"], "ccimg:", r["ccimg"], "cam_imgs:", r["cam_imgs"])
for r in with_word:
    if r not in with_cams:
        print(r["route"], "(word only, cams:", r.get("cam_imgs"), ")")

# collect unique image URLs across all
all_imgs = sorted({u for r in with_cams for u in (r.get("ccimg") or []) + (r.get("cam_imgs") or [])})
print("unique image urls:", len(all_imgs))
for u in all_imgs:
    print(" ", u)

with open(ROOT + r"\_bcf_route_cams.json", "w", encoding="utf-8") as f:
    json.dump({"pages": results, "unique_images": all_imgs}, f, indent=2)
print("saved")
