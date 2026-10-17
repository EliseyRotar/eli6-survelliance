# -*- coding: utf-8 -*-
import json
import re
import urllib.request
import urllib.error

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0"}


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read(4000)
    except Exception as e:
        return None, {}, str(e).encode()


st, h, b = fetch("https://transit.gencat.cat/ca/informacio-viaria/estat-transit/cameres-transit/")
print("cat_page", st, len(b))
open(ROOT + r"\_es_cat_page.html", "wb").write(b)

st, h, b2 = fetch("https://analisi.transparenciacatalunya.cat/resource/3tzz-6b9y.json?$limit=1000")
print("socrata", st, h.get("Content-Type"), len(b2))
open(ROOT + r"\_es_cat_socrata.json", "wb").write(b2)
try:
    d = json.loads(b2.decode("utf-8", "replace"))
    print("socrata items:", len(d))
    if d:
        print("item0:", json.dumps(d[0], ensure_ascii=False)[:700])
except Exception as e:
    print("socrata parse fail:", e)

t = open(ROOT + r"\_es_cat_xml.xml", encoding="utf-8", errors="replace").read()
print("XML len", len(t))
print("head:", t[:700].replace("\n", " "))
print("camera tags:", len(re.findall(r"<camara|<camera", t, re.I)))
media = re.findall(r"https?://[^<>\"]+?\.(?:jpg|png|gif|jpeg)", t, re.I)
print("xml media urls:", len(media), media[:5])

# gencat page hrefs
t = open(ROOT + r"\_es_cat_page.html", encoding="utf-8", errors="replace").read()
hrefs = sorted(set(re.findall(r'href="([^"]+)"', t)))
interesting = [x for x in hrefs if re.search(r"jpg|png|gif|pdf|cam|imat|video|popup|imatge", x, re.I)]
print("gencat page interesting hrefs:", len(interesting))
for x in interesting[:50]:
    print(" ", x)
