# -*- coding: utf-8 -*-
"""Session 46: live-feed recon + captions + coords + cadence for ccimg.bcferries.com."""
import re
import json
import time
import urllib.request
import urllib.error

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def fetch(url, method="GET", timeout=20):
    req = urllib.request.Request(url, headers=UA, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read(200000)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read(4000)
    except Exception as e:
        return None, {}, str(e).encode()


report = {}

# --- 1) DNS + InternetDB ---
print("== DNS/InternetDB ==")
import socket
ips = []
try:
    ips = sorted({ai[4][0] for ai in socket.getaddrinfo("ccimg.bcferries.com", 443)})
except Exception as e:
    print("dns fail", e)
print("ccimg.bcferries.com ->", ips)
for ip in ips:
    st, h, b = fetch(f"https://internetdb.shodan.io/{ip}")
    print("InternetDB", ip, st)
    try:
        print(" ", json.loads(b.decode()))
    except Exception:
        print(" ", b[:200])

# --- 2) stream-ish path probe on ccimg ---
print("== path probe on ccimg ==")
path_hits = []
probe_paths = [
    "/", "/cam1_TSA.mjpg", "/cam1_TSA.jpg", "/cam1_TSA/video", "/cam1_TSA/mjpg",
    "/axis-cgi/mjpg/video.cgi", "/video", "/mjpg", "/stream", "/live",
    "/cgi-bin/mjpg/video.cgi", "/cam1_TSA.cgi", "/videostream.cgi",
    "/isapi/Streaming/channels/101/httpGetSnapshot", "/onvif-http/snapshot",
    "/cc/support/terminals/", "/cc/support/", "/cc/",
]
for p in probe_paths:
    st, h, b = fetch("https://ccimg.bcferries.com" + p, timeout=12)
    ctype = h.get("Content-Type", "")
    print(f"  {p} -> {st} {ctype} len={len(b) if isinstance(b, (bytes, bytearray)) else '?'}")
    if st == 200:
        path_hits.append({"path": p, "status": st, "ctype": ctype, "len": len(b)})

# --- 3) capture headers for a cam (cadence) ---
print("== cam headers / cadence ==")
u = "https://ccimg.bcferries.com/cc/support/terminals/cam1_TSA.jpg"
st, h, b = fetch(u)
hdr_keys = ["Last-Modified", "Date", "ETag", "Cache-Control", "Expires", "Content-Length", "Server", "Content-Type"]
cam_hdrs = {k: h.get(k) for k in hdr_keys}
print("headers:", cam_hdrs)
time.sleep(70)
st2, h2, b2 = fetch(u)
cam_hdrs2 = {k: h2.get(k) for k in hdr_keys}
print("headers+70s:", cam_hdrs2)
changed = b != b2
print("image changed in 70s:", changed, "sizes:", len(b), len(b2))

# --- 4) caption scrape from webcams page ---
print("== captions ==")
with open(ROOT + r"\_bcf_webcams_page.html", encoding="utf-8") as f:
    whtml = f.read()
term_re = re.compile(
    r'<h6 class="webcam-h">\s*([^<]+?)\s*<i class="fa fa-angle-down pull-right"></i>\s*</h6>(.*?)<hr/>',
    re.S,
)
captions = {}
for m in term_re.finditer(whtml):
    term = m.group(1).replace("&nbsp;", " ").strip()
    block = m.group(2)
    for im in re.finditer(
        r'<img src="(https://ccimg\.bcferries\.com/[^"]+)"[^>]*>\s*<p[^>]*>\s*([^<]+?)\s*</p>',
        block,
    ):
        captions[im.group(1)] = {"terminal": term, "caption": im.group(2).strip()}
for k, v in captions.items():
    print(" ", k.split("/")[-1], v)

# route pages: extract any cam captions there too (sample a few)
print("== route page captions (sample) ==")
for path in ["/current-conditions/TSA-SWB", "/current-conditions/HSB-NAN", "/current-conditions/SWB-TSA", "/current-conditions/PSB-TSA", "/current-conditions/HRB-COR", "/current-conditions/PEN-CHM"]:
    st, h, b = fetch("https://www.bcferries.com" + path)
    html = b.decode("utf-8", "replace")
    found = re.findall(
        r'(https://ccimg\.bcferries\.com/cc/support/terminals/cam[^"]+)"[^>]*>\s*(?:</[^>]+>\s*)*<p[^>]*>\s*([^<]+?)\s*</p>',
        html,
    )
    # looser: any text after cam img
    found2 = re.findall(
        r'(cam\d_[A-Za-z]{3}\.jpg)"[^>]*>\s*</?[^>]*>?\s*<p[^>]*>\s*([^<]+)',
        html,
    )
    print(path, "strict:", found, "loose:", found2)
    # dump a snippet around first cam img
    i = html.find("terminals/cam")
    if i >= 0:
        print("  snippet:", re.sub(r"\s+", " ", html[i:i + 500])[:400])

# --- 5) terminal coordinates: try departures/terminal pages or known JSON ---
print("== terminal coords ==")
st, h, b = fetch("https://www.bcferries.com/current-conditions/departures")
dhtml = b.decode("utf-8", "replace")
# look for lat/lon patterns in departures page and webcams page
for name, page in [("departures", dhtml), ("webcams", whtml)]:
    coords = re.findall(r'"(?:lat|latitude)"\s*:\s*(-?\d+\.\d+).{0,40}?"(?:lon|lng|longitude)"\s*:\s*(-?\d+\.\d+)', page)
    coords2 = re.findall(r'(-?\d{2}\.\d{4,})\s*,\s*(-?\d{3}\.\d{4,})', page)
    print(name, "json-coords:", len(coords), coords[:5], "plain:", len(coords2), coords2[:5])

# terminal-directions pages: fetch the first terminal page slug pattern from sitemap
st, h, b = fetch("https://www.bcferries.com/sitemap")
sm = b.decode("utf-8", "replace")
term_pages = sorted(set(re.findall(r'href="([^"]*terminal[^"]*)"', sm)))
print("sitemap terminal links:", len(term_pages))
for t in term_pages[:20]:
    print(" ", t)

out = {
    "ips": ips,
    "path_hits": path_hits,
    "cam_headers_t0": cam_hdrs,
    "cam_headers_t70": cam_hdrs2,
    "image_changed_70s": changed,
    "captions_from_webcams_page": captions,
}
with open(ROOT + r"\_bcf_recon.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
print("saved recon")
