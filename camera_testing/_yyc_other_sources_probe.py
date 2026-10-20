# -*- coding: utf-8 -*-
"""Session 48f: probe AB511 Cctv history + trafficcalgary.ca API for archives."""
import os
import re
import subprocess

TEMP = os.environ["TEMP"]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def fetch(url, out_name, timeout=30):
    op = os.path.join(TEMP, out_name)
    p = subprocess.run(["curl", "-sL", "-A", UA, "--max-time", str(timeout),
                        "-o", op, "-w", "%{http_code}|%{content_type}|%{size_download}", url],
                       capture_output=True, text=True, timeout=timeout + 10)
    body = b""
    if os.path.exists(op):
        with open(op, "rb") as f:
            body = f.read()
    return p.stdout.strip(), body


print("=== AB511 Cctv viewer ===")
meta, body = fetch("https://511.alberta.ca/map/Cctv/138975", "ab511.html")
print("page:", meta)
text = body.decode("utf-8", "replace")
# image / history endpoints in page
for m in set(re.findall(r'https?://[^"\'\s<>]+', text)):
    if re.search(r'cctv|image|jpg|png|history|thumb|frame', m, re.I):
        print("  URL:", m[:160])
for m in set(re.findall(r'["\'](/[^"\']*(?:cctv|image|jpg|png|history|thumb)[^"\']*)["\']', text, re.I)):
    print("  rel:", m[:160])
# js bundle refs
for m in set(re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', text)):
    print("  js:", m[:160])

print("\n=== trafficcalgary.ca ===")
meta2, body2 = fetch("https://trafficcalgary.ca/", "tcagary2.html")
print("page:", meta2)
text2 = body2.decode("utf-8", "replace")
for m in set(re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', text2)):
    print("  js:", m[:160])
for m in set(re.findall(r'https?://[^"\'\s<>]+(?:api|json|feed)[^"\'\s<>]*', text2, re.I)):
    print("  api:", m[:160])
# inline hints of slideshow/history
for kw in ("slideshow", "timelapse", "history", "archive", "past", "previous"):
    for m in re.finditer(kw, text2, re.I):
        s = max(0, m.start() - 120)
        print("  [%s] …%s…" % (kw, text2[s:m.end() + 160].replace("\n", " ")[:280]))
        break
