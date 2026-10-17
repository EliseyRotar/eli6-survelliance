# -*- coding: utf-8 -*-
"""Session 46 recon: dump BC Ferries webcam inventory from site pages."""
import re
import json
import time
import urllib.request

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "replace")


# 1) dedicated webcams page
html = fetch("https://www.bcferries.com/current-conditions/webcams")
with open(ROOT + r"\_bcf_webcams_page.html", "w", encoding="utf-8") as f:
    f.write(html)
print("webcams page:", len(html), "bytes")

# extract cam images + surrounding terminal heading
cam_re = re.compile(
    r'<h6 class="webcam-h">\s*([^<]+?)\s*<i class="fa fa-angle-down pull-right"></i>\s*</h6>.*?</div>\s*<hr/>',
    re.S,
)
img_re = re.compile(r'<img src="(https://ccimg\.bcferries\.com/[^"]+)"[^>]*>')
term_re = re.compile(
    r'<h6 class="webcam-h">\s*([^<]+?)\s*<i class="fa fa-angle-down pull-right"></i>\s*</h6>(.*?)<hr/>',
    re.S,
)
cams = []
for m in term_re.finditer(html):
    term = m.group(1).replace("&nbsp;", " ").strip()
    for im in img_re.finditer(m.group(2)):
        cams.append({"terminal": term, "img": im.group(1)})
print("cam images on /current-conditions/webcams:", len(cams))
for c in cams:
    print(" ", c["terminal"], "->", c["img"])

# select options (terminal codes)
for m in re.finditer(r'<option value="([A-Z]{3})"', html):
    pass
codes = re.findall(r'<option value="([A-Z]{3})"', html)
print("terminal codes:", sorted(set(codes)))

# 2) current-conditions index (per-route cams)
try:
    cc = fetch("https://www.bcferries.com/current-conditions")
    with open(ROOT + r"\_bcf_current_conditions.html", "w", encoding="utf-8") as f:
        f.write(cc)
    cc_cams = sorted(set(re.findall(r'https://ccimg\.bcferries\.com/[^"\']+', cc)))
    print("current-conditions ccimg urls:", len(cc_cams))
    for u in cc_cams:
        print(" ", u)
    # find terminal/route links
    route_links = sorted(set(re.findall(r'href="(/current-conditions/[a-zA-Z0-9\-/]+)"', cc)))
    print("current-conditions links:", len(route_links))
    for u in route_links[:80]:
        print(" ", u)
except Exception as e:
    print("current-conditions fetch failed:", e)

with open(ROOT + r"\_bcf_cams_raw.json", "w", encoding="utf-8") as f:
    json.dump({"webcams_page": cams}, f, indent=2)
print("saved")
