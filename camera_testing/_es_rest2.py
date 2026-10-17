# -*- coding: utf-8 -*-
"""Session 47: vitoria geojson + euskadi admin fileUrls + host fixes + andorra/cantur probes."""
import json
import re
import ssl
import urllib.request
import urllib.error

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read(4000)
    except Exception as e:
        return None, {}, str(e).encode()


print("== vitoria geojson ==")
st, h, b = fetch("https://www.vitoria-gasteiz.org/c11-01w/cameras?action=list&format=GEOJSON")
print("vitoria:", st, len(b))
if st == 200:
    open(ROOT + r"\_es_vitoria.geojson", "wb").write(b)
    try:
        d = json.loads(b.decode("utf-8", "replace"))
        fs = d.get("features", [])
        print("  features:", len(fs))
        if fs:
            print("  f0:", json.dumps(fs[0], ensure_ascii=False)[:600])
    except Exception as e:
        print("  parse:", e, b[:150])

print("\n== euskal admin fileUrls ==")
d = json.load(open(ROOT + r"\_es_euskal_admin.json", encoding="utf-8-sig"))
for item in d:
    print(" ", item.get("sourceEs"), "->", item.get("fileUrl"))
    fu = item.get("fileUrl")
    if fu:
        st, h, b2 = fetch(fu, timeout=45)
        print("    fetch:", st, len(b2))
        if st == 200 and len(b2) > 50:
            name = re.sub(r"\W+", "_", fu.rsplit("/", 1)[-1])[:40]
            open(ROOT + f"\\_es_adm_{name}", "wb").write(b2)
            try:
                txt = b2.decode("utf-8-sig", "replace")
                if txt.lstrip().startswith("{") or txt.lstrip().startswith("["):
                    jj = json.loads(txt)
                    print("    json n:", len(jj))
                    print("    item0:", json.dumps(jj[0], ensure_ascii=False)[:400] if jj else "")
                elif "<" in txt[:200]:
                    print("    xml head:", txt[:300].replace("\n", " "))
                else:
                    print("    csv head:", txt.splitlines()[0][:200])
                    print("    lines:", len(txt.splitlines()))
            except Exception as e:
                print("    parse:", e)

print("\n== trafikoa host tests ==")
for u in ["https://www.trafikoa.eus/static/files/tr/camaras/819.jpg",
          "https://apps.trafikoa.euskadi.eus/static/files/tr/camaras/102.jpg",
          "http://www.trafikoa.eus/static/files/tr/camaras/819.jpg",
          "https://apps.trafikoa.euskadi.eus/wps/portal/trafico/camarasTrafico"]:
    st, h, b2 = fetch(u, timeout=25)
    print(" ", u, "->", st, h.get("Content-Type"), len(b2), h.get("Last-Modified"))

print("\n== andorra cam search on mobilitat.ad ==")
st, h, b2 = fetch("https://www.mobilitat.ad/", timeout=30)
if st == 200:
    t = b2.decode("utf-8", "replace")
    hits = [m.start() for m in re.finditer(r"(?i)c[aà]mer", t)]
    print(" cam mentions:", len(hits))
    for i in hits[:6]:
        print("  ctx:", re.sub(r"\s+", " ", t[max(0, i - 150):i + 200])[:350])
    # candidate section links
    hrefs = sorted(set(re.findall(r'href="([^"]+)"', t)))
    print(" more hrefs:", [x for x in hrefs if re.search(r"estat|vies|traf|map|webcam|transit", x, re.I)])

print("\n== andorra gif probes ==")
for u in ["https://app.mobilitat.ad/gifs/margineda.gif?a=1",
          "http://app.mobilitat.ad/gifs/margineda.gif",
          "https://app.mobilitat.ad/gifs/canillo.gif?a=1"]:
    st, h, b2 = fetch(u, timeout=20)
    print(" ", u, "->", st, h.get("Content-Type"), len(b2))

print("\n== cantur probes ==")
for u in ["https://cantur.com/camaras/VALLE/VALLE.jpg",
          "http://cantur.com/camaras/VALLE/VALLE.jpg",
          "https://www.cantur.com/camaras/",
          "https://cantur.com/"]:
    st, h, b2 = fetch(u, timeout=25)
    print(" ", u, "->", st, h.get("Content-Type"), len(b2))
