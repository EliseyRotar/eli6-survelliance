# -*- coding: utf-8 -*-
"""Session 47: pre-only ids, old-vs-prod diff, 8020 identity, camarasdgt road page."""
import json
import re
import urllib.request
import urllib.error

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Referer": "https://etraffic.dgt.es/etrafficWEB/"}


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read(400000)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read(4000)
    except Exception as e:
        return None, {}, str(e).encode()


prod = json.load(open(ROOT + r"\_es_camaras_etraffic.json", encoding="utf-8"))
pre = json.load(open(ROOT + r"\_es_camaras_pre.json", encoding="utf-8"))
old = json.load(open(ROOT + r"\_es_camaras_dgt.json", encoding="utf-8"))["camaras"]

prod_ids = {c["idCamara"] for c in prod["camaras"]}
old_ids = {c["id"] for c in old}
print("prod:", len(prod_ids), "old:", len(old_ids))
print("only in prod:", sorted(prod_ids - old_ids))
print("only in old:", sorted(old_ids - prod_ids))

print("\n== pre-only ids on prod image host ==")
for cid in ["176266", "993"]:
    u = f"{prod['urlBase']}{cid}.jpg"
    st, h, b = fetch(u)
    ok = st == 200 and "image" in h.get("Content-Type", "")
    print(f"  {u} -> {st} {h.get('Content-Type')} len={len(b)} {'ALIVE' if ok else ''}")
    if ok:
        # find in pre for metadata
        for c in pre["camaras"]:
            if c["idCamara"] == cid:
                print("    pre meta:", json.dumps(c, ensure_ascii=False))

print("\n== 8020 identity ==")
st, h, b = fetch("http://212.128.100.158:8020/", timeout=15)
body = b.decode("utf-8", "replace")
t = re.search(r"<title>(.*?)</title>", body, re.S | re.I)
print("title:", t.group(1).strip() if t else None)
print("headers:", {k: v for k, v in h.items() if k.lower() in ("server", "x-powered-by", "www-authenticate")})
print("head body:", body[:700])
links = re.findall(r'href="([^"]+)"', body)
print("links:", links[:20])
# common web-cam viewer paths on it
for p in ["/video", "/cam", "/axis-cgi/mjpg/video.cgi", "/mjpg/video.mjpg", "/cgi-bin/mjpg/video.cgi", "/Streaming/Channels/1/picture"]:
    st2, h2, b2 = fetch(f"http://212.128.100.158:8020{p}", timeout=8)
    ct = h2.get("Content-Type", "")
    if st2 and (st2 != 404 or "image" in ct):
        print(f"  {p} -> {st2} {ct} len={len(b2)}")

print("\n== camarasdgt road page ==")
st, h, b = fetch("https://www.camarasdgt.es/a-2/", timeout=25)
print("page:", st, len(b))
if st == 200:
    html = b.decode("utf-8", "replace")
    open(ROOT + r"\_es_camarasdgt_road.html", "w", encoding="utf-8").write(html)
    imgs = sorted(set(re.findall(r'https?://[^"\'\s>]+\.(?:jpg|jpeg|png|mjpg)[^"\'\s>]*', html, re.I)))
    print("imgs:", len(imgs))
    for u in imgs[:20]:
        print(" ", u)
    # maybe lazy-loaded via data attrs
    data = sorted(set(re.findall(r'data-[a-z-]+="([^"]*(?:jpg|http)[^"]*)"', html, re.I)))
    print("data attrs:", data[:10])
    # count camera entries
    print("cam-ish blocks:", len(re.findall(r'class="[^"]*camara', html, re.I)))
    # any embedded json
    j = re.findall(r'<script[^>]*>(.*?)</script>', html, re.S)
    for s in j:
        if "jpg" in s or "camara" in s.lower():
            print("script hit:", s[:500])
            break
