# -*- coding: utf-8 -*-
"""Session 47: Wayback coverage for camarasdgt listing pages."""
import json
import time
import urllib.request
import urllib.parse
import urllib.error

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def fetch(url, timeout=90, tries=4):
    for i in range(tries):
        req = urllib.request.Request(url, headers=UA)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and i < tries - 1:
                time.sleep(15 * (i + 1))
                continue
            return e.code, e.read(2000)
        except Exception:
            if i < tries - 1:
                time.sleep(5)
                continue
            return None, b""


# CDX for camarasdgt.es - collapse urlkey, from 2025
print("CDX camarasdgt.es ...", flush=True)
st, b = fetch("http://web.archive.org/cdx/search/cdx?url=camarasdgt.es/*&output=json&collapse=urlkey&filter=statuscode:200&from=2025&limit=10000")
print("status", st, "bytes", len(b))
try:
    arr = json.loads(b.decode())
    rows = arr[1:]
    print("rows:", len(rows))
    open(ROOT + r"\_es_cdx_camarasdgt.json", "w").write(json.dumps(arr))
    # how many listing-ish (depth 2)
    from urllib.parse import urlparse
    d2 = [r for r in rows if len(urlparse(r[2]).path.strip("/").split("/")) == 2]
    d1 = [r for r in rows if len(urlparse(r[2]).path.strip("/").split("/")) == 1]
    d3 = [r for r in rows if len(urlparse(r[2]).path.strip("/").split("/")) == 3]
    print("archived depth1:", len(d1), "depth2:", len(d2), "depth3:", len(d3))
    print("sample d2:", [r[2] for r in d2[:10]])
except Exception as e:
    print("parse fail", e, b[:200])
