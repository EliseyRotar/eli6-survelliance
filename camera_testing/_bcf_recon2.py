# -*- coding: utf-8 -*-
"""Session 46 part 2: subdomains, terminal coords, full captions, Last-Modified census."""
import re
import json
import urllib.request
import urllib.error
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read(8000)
    except Exception as e:
        return None, {}, str(e).encode()


out = {}

# --- 1) subdomain sweep ---
print("== hackertarget subdomains ==")
st, h, b = fetch("https://api.hackertarget.com/hostsearch/?q=bcferries.com", timeout=40)
subs = []
if st == 200 and not b.startswith(b"error"):
    txt = b.decode("utf-8", "replace")
    with open(ROOT + r"\_bcf_sub_bcferries_com.txt", "w", encoding="utf-8") as f:
        f.write(txt)
    for line in txt.splitlines():
        if "," in line:
            ip, host = line.split(",", 1)
            subs.append({"host": host.strip(), "ip": ip.strip()})
print("subdomains:", len(subs))
for s in subs:
    print(" ", s["host"], s["ip"])

# also th.gov.bc.ca already done in DriveBC; bcferries corp subs only here

# --- 2) busy-terminals page ---
print("== busy-terminals ==")
st, h, b = fetch("https://www.bcferries.com/current-conditions/busy-terminals")
bt = b.decode("utf-8", "replace")
with open(ROOT + r"\_bcf_busy_terminals.html", "w", encoding="utf-8") as f:
    f.write(bt)
coords = re.findall(r'(-?\d{2}\.\d{4,})\s*[,&"\']+\s*(-?\d{3}\.\d{4,})', bt)
latlons = re.findall(r'"(?:latitude|lat)"\s*:\s*(-?\d+\.\d+).{0,60}?"(?:longitude|lng|lon)"\s*:\s*(-?\d+\.\d+)', bt, re.S)
print("busy-terminals plain coords:", coords[:10], "json:", latlons[:10])

# --- 3) vessel tracking page ---
print("== vessel tracking ==")
st, h, b = fetch("https://www.bcferries.com/current-conditions/vessel-tracking-positions")
vt = b.decode("utf-8", "replace")
with open(ROOT + r"\_bcf_vessel_tracking.html", "w", encoding="utf-8") as f:
    f.write(vt)
# find script srcs and inline configs
scripts = re.findall(r'<script[^>]+src="([^"]+)"', vt)
print("scripts:", len(scripts))
for s in scripts:
    if any(k in s.lower() for k in ("track", "vessel", "map", "fleet", "position", "cam")):
        print("  interesting:", s)
# look for api urls inline
apis = sorted(set(re.findall(r'https?://[a-z0-9.\-]+bcferries\.com[^"\'\s<>]*', vt, re.I)))
print("inline bcferries urls:", len(apis))
for a in apis[:40]:
    print(" ", a)
# lat/lon in page
vt_coords = re.findall(r'(-?\d{2}\.\d{4,})\s*,\s*(-?\d{3}\.\d{4,})', vt)
print("vt plain coords sample:", vt_coords[:10], "count", len(vt_coords))

# --- 4) full caption+address extraction from all route pages ---
print("== full captions from route pages ==")
with open(ROOT + r"\_bcf_current_conditions.html", encoding="utf-8") as f:
    cc = f.read()
links = sorted(set(re.findall(r'href="(/current-conditions/([A-Z]{3})-([A-Z]{3}))"', cc)))
# unique terminal-oriented pages: keep one per route direction is fine; we merge by cam url


def scrape_route(item):
    path, a, bcode = item
    st, h, raw = fetch("https://www.bcferries.com" + path)
    html = raw.decode("utf-8", "replace")
    cams = []
    for m in re.finditer(
        r'<img src="(https://ccimg\.bcferries\.com/cc/support/terminals/cam[^"]+)"[^>]*>\s*'
        r'(?:<p class="text-center[^"]*">\s*([^<]*?)\s*</p>)?',
        html,
    ):
        cams.append({"url": m.group(1), "caption": (m.group(2) or "").strip()})
    # terminal name + address blocks
    terms = []
    for tm in re.finditer(
        r'<h4[^>]*><b>([^<]+)</b></h4>\s*<p[^>]*>\s*<span>#\s*([^<]+)</span>',
        html,
    ):
        terms.append({"name": tm.group(1).strip(), "address": tm.group(2).strip()})
    return {"path": path, "route": f"{a}-{bcode}", "cams": cams, "terminals": terms}


routes_data = []
with ThreadPoolExecutor(max_workers=8) as ex:
    futs = [ex.submit(scrape_route, it) for it in links]
    for i, fut in enumerate(as_completed(futs), 1):
        routes_data.append(fut.result())
        if i % 25 == 0:
            print(f"  {i}/{len(links)}")

# merge cam -> captions (union) + terminal info
cam_meta = {}
for r in routes_data:
    for c in r["cams"]:
        e = cam_meta.setdefault(c["url"], {"captions": set(), "routes": set()})
        if c["caption"]:
            e["captions"].add(c["caption"])
        e["routes"].add(r["route"])
    for t in r["terminals"]:
        pass

# also pull webcams-page captions
with open(ROOT + r"\_bcf_recon.json", encoding="utf-8") as f:
    recon = json.load(f)
for url, meta in recon.get("captions_from_webcams_page", {}).items():
    e = cam_meta.setdefault(url, {"captions": set(), "routes": set()})
    e["captions"].add(meta["caption"])
    e.setdefault("terminal_from_page", meta["terminal"])

print("cam urls with meta:", len(cam_meta))
for u, m in sorted(cam_meta.items()):
    print(" ", u.split("/")[-1], "caps:", sorted(m["captions"]))

# --- 5) Last-Modified census across all live cams ---
print("== Last-Modified census ==")
with open(ROOT + r"\_bcf_cams_probe.json", encoding="utf-8") as f:
    probe = json.load(f)
hits = [h for h in probe["hits"] if "_" in h["url"] and h["url"].lower().endswith(".jpg")]
# dedupe case-insensitive
seen = set()
uniq = []
for h in hits:
    k = h["url"].lower()
    if k not in seen:
        seen.add(k)
        uniq.append(h)
print("unique cams (case-insensitive):", len(uniq))


def head_cam(h):
    st, hdrs, _ = fetch(h["url"], timeout=15)
    return {
        "url": h["url"],
        "status": st,
        "last_modified": hdrs.get("Last-Modified"),
        "content_length": hdrs.get("Content-Length"),
        "server": hdrs.get("Server"),
    }


census = []
with ThreadPoolExecutor(max_workers=10) as ex:
    futs = [ex.submit(head_cam, h) for h in uniq]
    for fut in as_completed(futs):
        census.append(fut.result())
census.sort(key=lambda c: c["url"])
for c in census:
    print(" ", c["url"].split("/")[-1], c["last_modified"], c["content_length"])

out = {
    "subdomains": subs,
    "cam_meta": {u: {"captions": sorted(m["captions"]), "routes": sorted(m["routes"]), "terminal_from_page": m.get("terminal_from_page")} for u, m in cam_meta.items()},
    "census": census,
    "route_data_summary": [{"route": r["route"], "cams": r["cams"], "terminals": r["terminals"]} for r in routes_data],
}
with open(ROOT + r"\_bcf_recon2.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
print("saved recon2")
