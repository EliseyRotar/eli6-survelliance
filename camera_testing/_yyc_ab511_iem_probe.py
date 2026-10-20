# -*- coding: utf-8 -*-
"""Session 48g: AB511 /map/Cctv/<id>/<idx> range+spacing; IEM archive depth."""
import hashlib
import os
import re
import subprocess

TEMP = os.environ["TEMP"]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def get(url, out_name, timeout=25, headers=False):
    op = os.path.join(TEMP, out_name)
    args = ["curl", "-sL", "-A", UA, "--max-time", str(timeout),
            "-o", op, "-w", "%{http_code}|%{content_type}|%{size_download}"]
    if headers:
        args += ["-D", os.path.join(TEMP, "h.txt")]
    args.append(url)
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout + 8)
    hdr = {}
    if headers and os.path.exists(os.path.join(TEMP, "h.txt")):
        for line in open(os.path.join(TEMP, "h.txt"), encoding="latin-1"):
            if ":" in line and not line.startswith(" "):
                k, v = line.split(":", 1)
                hdr[k.lower()] = v.strip()
    body = b""
    if os.path.exists(op):
        with open(op, "rb") as f:
            body = f.read()
    return p.stdout.strip(), hdr, body


print("=== AB511 index probing (id 138975) ===")
cid = "138975"
results = []
for idx in (0, 1, 2, 3, 5, 10, 20, 29, 30, 31, 50, 99, 100, 101, 180, 360):
    meta, hdr, body = get("https://511.alberta.ca/map/Cctv/%s/%d" % (cid, idx),
                          "ab_%d.bin" % idx, headers=True)
    lm = hdr.get("last-modified", "")[:24]
    ct = meta.split("|")[1] if "|" in meta else ""
    ok = body[:2] == b"\xff\xd8"
    print("  idx %-4d -> %-30s lm=%s jpeg=%s md5=%s" % (
        idx, meta[:40], lm, ok, hashlib.md5(body).hexdigest()[:8] if ok else "-"))
    results.append((idx, ok, lm))

# also check a second camera id for same behavior
print("\nsecond cam id 139000ish sample:")
for idx in (1, 5):
    meta, hdr, body = get("https://511.alberta.ca/map/Cctv/139000/%d" % idx,
                          "ab2_%d.bin" % idx, headers=True)
    print("  idx %d -> %s jpeg=%s" % (idx, meta[:40], body[:2] == b"\xff\xd8"))

# spacing: fetch idx1 vs idx2 vs idx3 Last-Modified deltas printed above

# ---------- IEM depth ----------
print("\n=== IEM archive depth (KCCI-036) ===")
for ymd in ("2026/10/19", "2024/01/15", "2020/06/01", "2016/03/10", "2012/05/05", "2008/08/08"):
    url = "https://mesonet.agron.iastate.edu/archive/data/%s/camera/KCCI-036/" % ymd
    meta, hdr, body = get(url, "iem_%s.html" % ymd.replace("/", "_"))
    text = body.decode("utf-8", "replace")
    jpgs = re.findall(r'href=["\']([^"\']+\.jpg)["\']', text)
    print("  %s -> %s jpgs=%d first=%s" % (ymd, meta[:36], len(jpgs), jpgs[0] if jpgs else "-"))
