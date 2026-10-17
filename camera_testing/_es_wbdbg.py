# -*- coding: utf-8 -*-
import json
import re
import urllib.request

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
res = json.load(open(ROOT + r"\_es_arch_webcam.json", encoding="utf-8"))
print("pages:", len(res))
nonempty = [(u, r["imgs"]) for u, r in res.items() if r["imgs"]]
print("pages with imgs:", len(nonempty))
for u, imgs in nonempty[:10]:
    print(" ", u, imgs[:3])

u = "https://www.camarasdgt.es/webcam/alicante/benidorm/playa-de-benidorm/"
arr = json.load(open(ROOT + r"\_es_cdx_webcam.json"))
ts = None
for r in arr[1:]:
    if r[2] == u:
        ts = r[1]
        break
print("ts:", ts)
if ts:
    req = urllib.request.Request(f"https://web.archive.org/web/{ts}id_/{u}", headers={"User-Agent": "Mozilla/5.0"})
    b = urllib.request.urlopen(req, timeout=60).read()
    t = b.decode("utf-8", "replace")
    open(ROOT + r"\_es_arch_wb_sample.html", "w", encoding="utf-8").write(t)
    print("len", len(t))
    pats = [
        r"https?://[^\"'\s>]+\.(?:jpg|png|gif|jpeg)[^\"'\s>]*",
        r"data-src=\"[^\"]+\"",
        r"srcset=\"[^\"]+\"",
        r"RenderService[^\"']+",
        r"<iframe[^>]+src=\"[^\"]+\"",
        r"url\([^)]+\)",
    ]
    for pat in pats:
        hits = sorted(set(re.findall(pat, t, re.I)))
        print(pat[:35], "->", len(hits))
        for x in hits[:8]:
            print("    ", x[:180])
