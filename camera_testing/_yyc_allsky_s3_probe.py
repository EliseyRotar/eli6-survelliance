# -*- coding: utf-8 -*-
"""Session 48j: allsky.tv archive listing styles."""
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


urls = [
    "https://archive.allsky.tv/?list-type=2&prefix=AMS18/&max-keys=20",
    "https://archive.allsky.tv/?prefix=AMS18/&max-keys=20",
    "https://archive.allsky.tv/?list-type=2&prefix=AMS18/LATEST/",
    "https://archive.allsky.tv/AMS18?list-type=2&max-keys=20",
    "https://archive.allsky.tv/AMS18/LATEST/010103.jpg",
    "https://archive.allsky.tv/AMS18/20261019/",
    "https://archive.allsky.tv/AMS18/2026/10/",
]
for i, u in enumerate(urls):
    m, b = get(u, "as_%d.bin" % i)
    t = b.decode("utf-8", "replace")
    keys = re.findall(r"<Key>([^<]+)</Key>", t)
    print("%-68s -> %s keys=%s" % (u[:68], m[:40], keys[:6] if keys else t[:100].replace("\n", " ")))
