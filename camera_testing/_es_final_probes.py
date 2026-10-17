# -*- coding: utf-8 -*-
"""Session 47: webcam subtree check + getFilteredData shape probe."""
import base64
import json
import re
import urllib.request
import urllib.parse
import urllib.error

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Referer": "https://etraffic.dgt.es/etrafficWEB/"}


def fetch(url, timeout=40, data=None, method=None):
    req = urllib.request.Request(url, data=data, headers=UA, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read(4000)
    except Exception as e:
        return None, {}, repr(e).encode()


def ps_decode(raw):
    txt = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    b = base64.b64decode(txt)
    return bytes(x ^ 0x66 for x in b).decode("utf-8")


txt = open(ROOT + r"\_es_camarasdgt_sitemap_index.xml", encoding="utf-8").read()
locs = re.findall(r"<loc>(.*?)</loc>", txt)
web = [u for u in locs if "/webcam/" in u]
print("webcam urls:", len(web))
for u in web[:15]:
    print(" ", u)

print("\n== getFilteredData probe ==")
for body in [b'{}', b'{"filters":[]}', b'{"caracter":"acontecimiento"}']:
    st, h, b = fetch("https://etraffic.dgt.es/etrafficWEB/api/cache/getFilteredData",
                     data=body, method="POST", timeout=40)
    print(" body", body, "->", st, len(b))
    if st == 200 and b:
        try:
            d = json.loads(ps_decode(b))
            print("  keys:", list(d.keys()))
            for k, v in d.items():
                if isinstance(v, list):
                    print(f"   {k}: n={len(v)}", json.dumps(v[0], ensure_ascii=False)[:300] if v else "")
            break
        except Exception as e:
            print("  decode/parse fail:", e, b[:80])

print("\n== getPMVs probe ==")
st, h, b = fetch("https://etraffic.dgt.es/etrafficWEB/api/cache/getPMVs", data=b"", method="POST", timeout=40)
print(" pmvs ->", st, len(b))
if st == 200 and b:
    try:
        d = json.loads(ps_decode(b))
        print("  keys:", list(d.keys()))
        for k, v in d.items():
            if isinstance(v, list):
                print(f"   {k}: n={len(v)}", json.dumps(v[0], ensure_ascii=False)[:300] if v else "")
    except Exception as e:
        print("  fail:", e)
