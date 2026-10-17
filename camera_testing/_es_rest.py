# -*- coding: utf-8 -*-
"""Session 47: remaining municipal/regional sources."""
import json
import re
import urllib.request
import urllib.error

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read(4000)
    except Exception as e:
        return None, {}, str(e).encode()


print("== euskal admin cams ==")
st, h, b = fetch("https://opendata.euskadi.eus/contenidos/ds_localizaciones/camaras_trafico_euskal_admin/opendata/traffic-cameras.json")
print("admin json:", st, len(b))
if st == 200:
    open(ROOT + r"\_es_euskal_admin.json", "wb").write(b)
    try:
        d = json.loads(b.decode("utf-8-sig"))
        print("  n:", len(d))
        print("  item0:", json.dumps(d[0], ensure_ascii=False)[:500])
    except Exception as e:
        print("  parse:", e, b[:120])

print("\n== vitoria airea page ==")
st, h, b = fetch("https://www.euskadi.eus/camaras-trafico-tiempo-real/web01-a2ingair/eu/")
print("airea:", st, len(b))
if st == 200:
    t = b.decode("utf-8", "replace")
    open(ROOT + r"\_es_airea.html", "w", encoding="utf-8").write(t)
    links = sorted(set(re.findall(r'href="([^"]+)"', t)))
    for x in links:
        if re.search(r"geojson|json|xml|txt|odt|csv|descarga|download", x, re.I):
            print("  ", x)

print("\n== cat image liveness ==")
for u in ["http://mct.gencat.cat/mct2bo/RenderService?sctidcam=nc87.gif",
          "https://mct.gencat.cat/mct2bo/RenderService?sctidcam=nc87.jpg",
          "https://mct.gencat.cat/mct2bo/RenderService?sctidcam=cb1.jpg"]:
    st, h, b = fetch(u, timeout=25)
    print(" ", u, "->", st, h.get("Content-Type"), len(b), h.get("Last-Modified"))

print("\n== euskadi json liveness ==")
st, h, b = fetch("https://www.trafikoa.eus/static/files/tr/camaras/819.jpg", timeout=20)
print(" trafikoa 819:", st, h.get("Content-Type"), len(b), h.get("Last-Modified"))

print("\n== andorra mobilitat ==")
for u in ["https://www.mobilitat.ad/", "https://app.mobilitat.ad/", "https://app.mobilitat.ad/gifs/margineda.gif"]:
    st, h, b = fetch(u, timeout=25)
    print(" ", u, "->", st, h.get("Content-Type"), len(b))
    if st == 200 and "text/html" in h.get("Content-Type", ""):
        t = b.decode("utf-8", "replace")
        hrefs = sorted(set(re.findall(r'href="([^"]+)"', t)))
        print("   hrefs:", hrefs[:30])
        gifs = sorted(set(re.findall(r'https?://[^"\'\s>]+\.gif', t, re.I)))
        print("   gifs:", gifs[:20])

print("\n== cantur ==")
st, h, b = fetch("https://cantur.com/camaras/", timeout=25)
print(" cantur:", st, h.get("Content-Type"), len(b))
if st == 200:
    t = b.decode("utf-8", "replace")
    open(ROOT + r"\_es_cantur.html", "w", encoding="utf-8").write(t)
    imgs = sorted(set(re.findall(r'https?://[^"\'\s>]+\.(?:jpg|gif|png)[^"\'\s]*', t, re.I)))
    print(" imgs:", len(imgs))
    for x in imgs[:30]:
        print("  ", x)
