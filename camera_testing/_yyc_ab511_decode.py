# -*- coding: utf-8 -*-
"""Session 48g2: decode AB511 /map/Cctv/<id>/<idx> semantics + IEM cam list."""
import hashlib
import os
import re
import subprocess

TEMP = os.environ["TEMP"]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def get(url, out_name, timeout=25):
    op = os.path.join(TEMP, out_name)
    p = subprocess.run(["curl", "-sL", "-A", UA, "--max-time", str(timeout),
                        "-o", op, "-w", "%{http_code}|%{content_type}|%{size_download}", url],
                       capture_output=True, text=True, timeout=timeout + 8)
    body = b""
    if os.path.exists(op):
        with open(op, "rb") as f:
            body = f.read()
    return p.stdout.strip(), body


print("=== does id matter? ===")
for url, name in [
    ("https://511.alberta.ca/map/Cctv/9999999/1", "x1.bin"),
    ("https://511.alberta.ca/map/Cctv/139001/1", "x2.bin"),
    ("https://511.alberta.ca/map/Cctv/138975/1", "x3.bin"),
    ("https://511.alberta.ca/map/Cctv/138975/1?cb=99", "x4.bin"),
    ("https://511.alberta.ca/map/Cctv/138975/2", "x5.bin"),
    ("https://511.alberta.ca/map/Cctv/139001/2", "x6.bin"),
    ("https://511.alberta.ca/map/Cctv/138975/6", "x7.bin"),
    ("https://511.alberta.ca/map/Cctv/138975/7", "x8.bin"),
]:
    meta, body = get(url, name)
    h = hashlib.md5(body).hexdigest()[:10] if body else "-"
    print("  %-55s %-30s md5=%s jpeg=%s" % (url[:55], meta[:30], h, body[:2] == b"\xff\xd8"))

print("\n=== myCctv bundle ===")
meta, body = get("https://511.alberta.ca/bundles/myCctv", "mycctv.js")
print("bundle:", meta, "len", len(body))
text = body.decode("utf-8", "replace")
for kw in ("map/Cctv", "Cctv/", "slick", "history", "Images", "getImages", "imageIndex", "frame"):
    for m in re.finditer(re.escape(kw), text, re.I):
        s = max(0, m.start() - 200)
        print("  [%s] …%s…" % (kw, text[s:m.end() + 260].replace("\n", " ")[:440]))
        break

print("\n=== myCameraTooltip.min.js ===")
meta, body = get("https://511.alberta.ca/Scripts/map/LayerSpecific/myCameraTooltip.min.js?v=26.08.30", "tip.js")
print("tip:", meta, "len", len(body))
t = body.decode("utf-8", "replace")
for m in re.finditer(r'Cctv', t):
    s = max(0, m.start() - 200)
    print("  …%s…" % t[s:m.end() + 300].replace("\n", " ")[:480])
    break
for m in re.finditer(r'(history|slideshow|carousel|previous|past)', t, re.I):
    s = max(0, m.start() - 150)
    print("  [%s] …%s…" % (m.group(1), t[s:m.end() + 220].replace("\n", " ")[:380]))

print("\n=== IEM unique cams in CSV ===")
import csv
cams = {}
with open(r"C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv",
          encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        u = row.get("live_stream_url") or row.get("url") or ""
        if "mesonet.agron.iastate.edu" in u:
            m = re.search(r"camera/([A-Za-z0-9-]+)/", u)
            if m:
                cams.setdefault(m.group(1), []).append((row.get("idx"), u))
for c, rows in sorted(cams.items()):
    print("  %-12s rows=%d e.g. %s" % (c, len(rows), rows[0][1][:110]))
