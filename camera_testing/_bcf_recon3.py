# -*- coding: utf-8 -*-
"""Session 46 part 3: API gateway, cc origin, terminal pages, coords, unlinked cams."""
import re
import json
import urllib.request
import urllib.error
import socket

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read(12000)
    except Exception as e:
        return None, {}, str(e).encode()


out = {}

# --- 1) cc.bcferries.com origin check ---
print("== cc.bcferries.com ==")
for path in [
    "/cc/support/terminals/cam1_TSA.jpg",
    "/cc/support/terminals/cam2_HSB.jpg",
    "/cc/support/terminals/cam2_PWR.jpg",
    "/",
]:
    st, h, b = fetch("https://cc.bcferries.com" + path)
    print(f"  {path} -> {st} {h.get('Content-Type')} len={len(b)} server={h.get('Server')}")
    if st == 200 and h.get("Content-Type", "").startswith("image"):
        print("    ORIGIN SERVES IMAGES, last-mod:", h.get("Last-Modified"))

# try http
st, h, b = fetch("http://cc.bcferries.com/cc/support/terminals/cam1_TSA.jpg")
print("  http:", st, h.get("Content-Type"), len(b))

# --- 2) apigateway ---
print("== apigateway ==")
for path in ["/", "/webcams", "/api/webcams", "/cameras", "/api", "/health", "/current-conditions"]:
    st, h, b = fetch("https://apigateway.bcferries.com" + path, timeout=12)
    print(f"  {path} -> {st} {h.get('Content-Type')} {b[:120]!r}")

# --- 3) www site: look for XHR/api in webcams page JS ---
print("== site JS api refs ==")
with open(ROOT + r"\_bcf_webcams_page.html", encoding="utf-8") as f:
    whtml = f.read()
# inline script urls / ajax endpoints
ajax = sorted(set(re.findall(r'["\'](/[a-zA-Z0-9_\-/\.]*(?:api|json|ajax|service|rest)[a-zA-Z0-9_\-/\.]*)["\']', whtml)))
print("ajax-ish paths:", ajax)
# external js
for m in re.finditer(r'<script[^>]+src="([^"]+)"', whtml):
    src = m.group(1)
    if "theme-bcf" in src or "jquery" in src.lower():
        continue
    print(" script:", src)
    if src.startswith("/"):
        st, h, b = fetch("https://www.bcferries.com" + src, timeout=20)
        if st == 200:
            js = b.decode("utf-8", "replace")
            hits = sorted(set(re.findall(r'["\'](/[a-zA-Z0-9_\-/]*(?:webcam|camera|cam)[a-zA-Z0-9_\-/]*)["\']', js, re.I)))
            apiish = sorted(set(re.findall(r'https?://[a-z0-9.\-]+bcferries[^"\'\s]*', js, re.I)))
            if hits or apiish:
                print("   cam paths:", hits, "urls:", apiish[:10])

# --- 4) terminal detail pages for the 5 majors + HSB + PWR for unlinked cams ---
print("== terminal detail pages ==")
term_pages = [
    "https://www.bcferries.com/travel-boarding/terminal-directions-parking-food/vancouver-tsawwassen/TSA",
    "https://www.bcferries.com/travel-boarding/terminal-directions-parking-food/victoria-swartz-bay/SWB",
    "https://www.bcferries.com/travel-boarding/terminal-directions-parking-food/vancouver-horseshoe-bay/HSB",
    "https://www.bcferries.com/travel-boarding/terminal-directions-parking-food/powell-river-westview/PWR",
]
term_info = {}
for url in term_pages:
    st, h, b = fetch(url)
    html = b.decode("utf-8", "replace")
    name = re.search(r'<h1[^>]*>\s*([^<]+?)\s*</h1>', html)
    cams = sorted(set(re.findall(r'cam\d_[A-Za-z]{3}\.jpg', html)))
    coords = re.findall(r'(-?\d{2}\.\d{4,})\s*,\s*(-?\d{3}\.\d{4,})', html)
    # maps links
    gmaps = re.findall(r'https://(?:www\.)?google\.[a-z.]+/maps[^"\']*', html)
    # schema.org geo
    geo = re.findall(r'"(?:latitude|longitude)"\s*:\s*(-?\d+\.\d+)', html)
    addr = re.search(r'<address[^>]*>(.*?)</address>', html, re.S)
    print(url.split("/")[-1], "st", st, "name", name.group(1) if name else None, "cams", cams, "coords", coords[:3], "geo", geo[:4], "gmaps", len(gmaps))
    term_info[url] = {"status": st, "cams": cams, "coords": coords[:5], "geo": geo, "gmaps": gmaps[:2]}
    # save
    fn = url.rstrip("/").split("/")[-1]
    with open(ROOT + rf"\_bcf_term_{fn}.html", "w", encoding="utf-8") as f:
        f.write(html)

# --- 5) check busy-terminals page source for terminal list with coords ---
print("== busy-terminals parse ==")
with open(ROOT + r"\_bcf_busy_terminals.html", encoding="utf-8") as f:
    bt = f.read()
print("len", len(bt))
# any data attributes
dattrs = re.findall(r'data-[a-z\-]+="[^"]{0,80}"', bt)
print("data attrs sample:", dattrs[:30])
# terminal names
btnames = re.findall(r'<h[3-6][^>]*>\s*([^<]{3,60})\s*</h[3-6]>', bt)
print("headings:", btnames[:30])

# --- 6) mqtt endpoints (vessel tracking, not cams but note) ---
print("== mqtt probe ==")
for host in ["prod.mqtt.bcferries.com"]:
    try:
        ips = sorted({ai[4][0] for ai in socket.getaddrinfo(host, 443)})
        print(host, ips)
        for ip in ips:
            st, h, b = fetch(f"https://internetdb.shodan.io/{ip}")
            print(" InternetDB", ip, b[:200])
    except Exception as e:
        print(host, "fail", e)

# --- 7) try common app API hosts ---
print("== app api hosts ==")
for host in ["api.bcferries.com", "app.bcferries.com", "mobile.bcferries.com", "services.bcferries.com", "data.bcferries.com"]:
    try:
        ips = socket.getaddrinfo(host, 443)
        print(host, "->", sorted({ai[4][0] for ai in ips}))
    except Exception:
        print(host, "NXDOMAIN")

with open(ROOT + r"\_bcf_recon3.json", "w", encoding="utf-8") as f:
    json.dump({"term_info": term_info}, f, indent=2)
print("saved recon3")
