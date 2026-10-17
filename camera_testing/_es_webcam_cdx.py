# -*- coding: utf-8 -*-
"""Session 47: CDX for webcam subtree + 415 content-type retries."""
import json
import time
import urllib.request
import urllib.parse
import urllib.error

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def fetch(url, timeout=90, tries=3, data=None, method=None, headers=None):
    hh = dict(UA)
    if headers:
        hh.update(headers)
    for i in range(tries):
        req = urllib.request.Request(url, data=data, headers=hh, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and i < tries - 1:
                time.sleep(12)
                continue
            return e.code, dict(e.headers), e.read(3000)
        except Exception:
            if i < tries - 1:
                time.sleep(4)
                continue
            return None, {}, b""


print("== CDX webcam subtree ==")
st, h, b = fetch("http://web.archive.org/cdx/search/cdx?url=" +
                 urllib.parse.quote("camarasdgt.es/webcam/*") +
                 "&output=json&collapse=urlkey&filter=statuscode:200&limit=5000")
print("status", st, len(b))
try:
    arr = json.loads(b.decode())
    rows = arr[1:]
    print("rows:", len(rows))
    json.dump(arr, open(ROOT + r"\_es_cdx_webcam.json", "w"))
    for r in rows[:40]:
        print("  ", r[1], r[2])
except Exception as e:
    print("parse:", e, b[:200])

print("\n== 415 content-type retries ==")
u = "https://etraffic.dgt.es/etrafficWEB/api/cache/getPMVs"
for ct, body in [("text/plain", b"{}"), ("application/x-www-form-urlencoded", b""),
                 ("application/json; charset=UTF-8", b"{}"), (None, b"")]:
    hh = {"Referer": "https://etraffic.dgt.es/etrafficWEB/"}
    if ct:
        hh["Content-Type"] = ct
    st, h, b = fetch(u, timeout=30, tries=1, data=body if body or ct else None,
                     method="POST" if ct or body is not None else None, headers=hh)
    print(f"  ct={ct} -> {st} len={len(b)}")
