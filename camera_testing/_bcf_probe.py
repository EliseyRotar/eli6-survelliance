# -*- coding: utf-8 -*-
"""Session 46: terminal catalog + brute-force cam URL probe."""
import re
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
        return r.status, r.headers, data


# 1) terminal directory page
status, hdrs, body = fetch("https://www.bcferries.com/travel-boarding/terminal-directions-parking-food")
html = body.decode("utf-8", "replace")
with open(ROOT + r"\_bcf_terminals_page.html", "w", encoding="utf-8") as f:
    f.write(html)
print("terminals page:", status, len(html))

# terminal links typically /travel-boarding/terminal-directions-parking-food/<slug>
term_links = sorted(set(re.findall(
    r'href="(/travel-boarding/terminal-directions-parking-food/([a-z0-9\-]+))"', html)))
print("terminal page slugs:", len(term_links))
for _, slug in term_links:
    print(" ", slug)

# extract any code+name pairs from dropdowns/selects
codes_names = {}
for m in re.finditer(r'<option[^>]*value="([A-Z]{3})"[^>]*>([^<]+)</option>', html):
    codes_names[m.group(1)] = m.group(2).strip()
print("select codes:", codes_names)

# 2) brute-force probe camN_CODE.jpg on ccimg
# collect candidate codes: from route sweep + select + slugs
codes = set(codes_names.keys())
# from route sweep json
with open(ROOT + r"\_bcf_route_cams.json", encoding="utf-8") as f:
    rc = json.load(f)
for u in rc["unique_images"]:
    m = re.search(r'/terminals/cam\d_([A-Za-z]{3})\.jpg', u)
    if m:
        codes.add(m.group(1).upper())
# from dedicated webcams page
with open(ROOT + r"\_bcf_cams_raw.json", encoding="utf-8") as f:
    raw = json.load(f)
for c in raw["webcams_page"]:
    m = re.search(r'cam\d_([A-Z]{3})\.jpg', c["img"])
    if m:
        codes.add(m.group(1))
print("candidate terminal codes:", sorted(codes))

def probe(url):
    try:
        req = urllib.request.Request(url, headers=UA, method="GET")
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read(64)
            ctype = r.headers.get("Content-Type", "")
            clen = r.headers.get("Content-Length", "?")
            return url, r.status, ctype, clen
    except Exception as e:
        code = getattr(e, "code", None)
        return url, code or str(e), "", ""

hits = []
urls = []
for n in range(1, 7):
    for code in sorted(codes):
        for case in (code, code.lower()):
            urls.append(f"https://ccimg.bcferries.com/cc/support/terminals/cam{n}_{case}.jpg")
# dedupe
urls = sorted(set(urls))
print("probing", len(urls), "urls ...")
with ThreadPoolExecutor(max_workers=12) as ex:
    futs = [ex.submit(probe, u) for u in urls]
    for fut in as_completed(futs):
        u, st, ct, cl = fut.result()
        if st == 200 and "image" in ct:
            hits.append({"url": u, "status": st, "ctype": ct, "clen": cl})
            print(" HIT", u, ct, cl)

hits.sort(key=lambda h: h["url"])
print("live cam urls:", len(hits))
with open(ROOT + r"\_bcf_cams_probe.json", "w", encoding="utf-8") as f:
    json.dump({"codes": sorted(codes), "hits": hits}, f, indent=2)
print("saved")
