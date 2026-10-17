# -*- coding: utf-8 -*-
"""Session 47: legacy infocar path + pre-env compare + camarasdgt + port 8020."""
import base64
import json
import re
import urllib.request
import urllib.error

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Referer": "https://etraffic.dgt.es/"}


def fetch(url, timeout=30, data=None, method=None, headers=None):
    hh = dict(UA)
    if headers:
        hh.update(headers)
    req = urllib.request.Request(url, data=data, headers=hh, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read(600000)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read(4000)
    except Exception as e:
        return None, {}, str(e).encode()


def ps_decode(raw):
    txt = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    b = base64.b64decode(txt)
    return bytes(x ^ 0x66 for x in b).decode("utf-8")


print("== legacy infocar path ==")
for cam_id in ["598", "176130", "2", "164700", "168411"]:
    u = f"https://infocar.dgt.es/etraffic/data/camaras/{cam_id}.jpg"
    st, h, b = fetch(u, timeout=20)
    ct = h.get("Content-Type", "")
    ok = st == 200 and "image" in ct and len(b) > 2000
    print(f"  {u} -> {st} {ct} len={len(b)} {'OK' if ok else ''} lm={h.get('Last-Modified')}")
    if st == 200 and "text/html" in ct:
        print("    body:", b[:200])

# try listing legacy dir
st, h, b = fetch("https://infocar.dgt.es/etraffic/data/camaras/", timeout=15)
print("legacy dir:", st, h.get("Content-Type"), len(b), b[:200])
st, h, b = fetch("https://infocar.dgt.es/etraffic/", timeout=15)
print("etraffic root:", st, h.get("Content-Type"), len(b), b[:300])

print("\n== pre-env decode & compare ==")
raw = open(ROOT + r"\_es_pre_getCamaras.raw", "rb").read()
try:
    d = json.loads(ps_decode(raw))
    pre = d["camaras"]
    print("pre cams:", len(pre), "urlBase:", d["urlBase"])
    prod = json.load(open(ROOT + r"\_es_camaras_etraffic.json", encoding="utf-8"))["camaras"]
    pre_ids = {c["idCamara"] for c in pre}
    prod_ids = {c["idCamara"] for c in prod}
    print("prod:", len(prod_ids), "only in pre:", sorted(pre_ids - prod_ids)[:30], "count:", len(pre_ids - prod_ids))
    print("only in prod:", sorted(prod_ids - pre_ids)[:30], "count:", len(prod_ids - pre_ids))
    open(ROOT + r"\_es_camaras_pre.json", "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=1))
except Exception as e:
    print("decode fail:", e, raw[:200])

print("\n== camarasdgt.es ==")
st, h, b = fetch("https://www.camarasdgt.es/", timeout=25)
print("home:", st, len(b))
if st == 200:
    html = b.decode("utf-8", "replace")
    open(ROOT + r"\_es_camarasdgt_home.html", "w", encoding="utf-8").write(html)
    imgs = sorted(set(re.findall(r'https?://[^"\'\s>]+(?:jpg|jpeg|png|mjpg|m3u8|video)[^"\'\s>]*', html, re.I)))
    print("media urls:", len(imgs))
    for u in imgs[:25]:
        print(" ", u)
    links = sorted(set(re.findall(r'href="([^"]+)"', html)))
    print("links sample:", links[:30])

print("\n== port 8020 probe ==")
for host in ["212.128.100.158", "212.128.100.139"]:
    for scheme in ["http", "https"]:
        st, h, b = fetch(f"{scheme}://{host}:8020/", timeout=10)
        ct = h.get("Content-Type", "")
        print(f"  {scheme}://{host}:8020/ -> {st} {ct} len={len(b)}")
        if st and st != 404:
            print("    body:", b[:300])
