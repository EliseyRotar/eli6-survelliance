# -*- coding: utf-8 -*-
"""Session 47: parse cat XML + euskadi fixes + next sources."""
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


print("== cat XML parse ==")
t = open(ROOT + r"\_es_cat_xml.xml", encoding="utf-8", errors="replace").read()
feats = re.findall(r"<gml:featureMember>(.*?)</gml:featureMember>", t, re.S)
print("features:", len(feats))
if feats:
    print("feat0:\n", feats[0][:1200])
# field names
fields = sorted(set(re.findall(r"<cite:(\w+)>", t)))
print("fields:", fields)
# extract cam id + point + others
cams = []
for f in feats:
    rec = dict(re.findall(r"<cite:(\w+)>([^<]*)</cite:\w+>", f))
    m = re.search(r"<gml:Point>.*?<gml:pos>([-\d.]+) ([-\d.]+)</gml:pos>", f, re.S)
    if m:
        rec["_lon"], rec["_lat"] = m.group(1), m.group(2)
    m2 = re.search(r"sctidcam=([^\"'&]+)", f)
    if m2:
        rec["_imgid"] = m2.group(1)
    cams.append(rec)
print("parsed cams:", len(cams))
json.dump(cams, open(ROOT + r"\_es_cat_cams.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
withimg = [c for c in cams if "_imgid" in c]
print("with img id:", len(withimg))
print("sample:", json.dumps(withimg[:3], ensure_ascii=False, indent=1))

print("\n== euskadi json raw head ==")
raw = open(ROOT + r"\_es_euskadi_json.json", "rb").read()
print(raw[:120])
try:
    d = json.loads(raw.decode("utf-8-sig"))
    print("parsed:", type(d).__name__, len(d) if hasattr(d, "__len__") else "")
    if isinstance(d, dict):
        print("keys:", list(d.keys())[:8])
except Exception as e:
    print("fail:", e)
    # try JSONP
    m = re.match(rb"^\s*(?:/\*.*?\*/\s*)?([\(\[])", raw)
    print("starts with:", raw[:30])

print("\n== euskadi admins links ==")
h = open(ROOT + r"\_es_euskadi_admins.html", encoding="utf-8", errors="replace").read()
links = sorted(set(re.findall(r'href="([^"]+)"', h)))
for x in links:
    if re.search(r"csv|json|geojson|xls|xml|opendata|download|descarga", x, re.I):
        print(" ", x)
