# -*- coding: utf-8 -*-
"""Session 48h: probe allsky archive + MBJB dated dirs; print wayback log."""
import os
import re
import subprocess

TEMP = os.environ["TEMP"]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def get(url, name):
    op = os.path.join(TEMP, name)
    p = subprocess.run(["curl", "-sL", "-A", UA, "--max-time", "25", "-o", op,
                        "-w", "%{http_code}|%{content_type}|%{size_download}", url],
                       capture_output=True, text=True, timeout=35)
    body = open(op, "rb").read() if os.path.exists(op) else b""
    return p.stdout.strip(), body


for u, n in [
    ("https://archive.allsky.tv/AMS18/", "as1.html"),
    ("https://archive.allsky.tv/", "as2.html"),
    ("https://archive.allsky.tv/AMS18/2026/10/19/", "as3.html"),
    ("https://itrafik.mbjb.gov.my/itrafik/cctv_snapshots/L03_Cam1/", "mbjb1.html"),
    ("https://itrafik.mbjb.gov.my/itrafik/cctv_snapshots/L03_Cam1/2026-07-18/", "mbjb2.html"),
]:
    m, b = get(u, n)
    t = b.decode("utf-8", "replace")
    links = re.findall(r'href=["\']([^"\']+)["\']', t)
    print("%-70s -> %s links=%s" % (u[:70], m[:44], links[:8]))
