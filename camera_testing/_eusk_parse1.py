# -*- coding: utf-8 -*-
import json
import re

def strip(s):
    return re.sub(r"\s+", " ", s).strip()

def head(name, path, n=1200):
    try:
        h = open(path, encoding="utf-8", errors="replace").read()
    except Exception as e:
        print(f"== {name} ERR {e}")
        return
    print(f"== {name} len={len(h)}")

# 1) Donostia cam page: look for image urls / json / api
h = open(r"C:\Users\ELI6-A~1\AppData\Local\Temp\dn_cams.html", encoding="utf-8", errors="replace").read()
print("== dn_cams.html len", len(h))
t = re.search(r"<title>([^<]*)</title>", h, re.I)
print(" title:", t.group(1).strip() if t else None)
imgs = sorted(set(re.findall(r"(?:src|href)=[\"']([^\"']+\.(?:jpg|jpeg|png|gif)[^\"']*)[\"']", h, re.I)))
print(" imgs:", len(imgs))
for i in imgs[:30]:
    print("   ", i[:150])
js = sorted(set(re.findall(r"(?:src|href)=[\"']([^\"']+\.(?:js|json)[^\"']*)[\"']", h, re.I)))
print(" js:", len(js))
for i in js[:20]:
    print("   ", i[:150])
for m in re.finditer(r"(camara[^\"'<> ]{0,80}|fwCam[^\"'<> ]{0,80})", h, re.I):
    pass
# inline camera config?
for m in re.finditer(r"(\{[^{}]{0,300}(?:lat|Lat|coord)[^{}]{0,300}\})", h):
    print(" CFG:", m.group(1)[:300])
# select options with camera names
opts = re.findall(r"<option[^>]*>([^<]+)</option>", h)
print(" options:", len(opts))
for o in opts[:40]:
    print("   opt:", strip(o)[:100])

# 2) Euskadi open data page: find JSON/API links
h2 = open(r"C:\Users\ELI6-A~1\AppData\Local\Temp\euskadi_od.html", encoding="utf-8", errors="replace").read()
links = sorted(set(re.findall(r"href=[\"']([^\"']+)[\"']", h2)))
hits = [l for l in links if re.search(r"json|api|rest|descarg|download|csv|xml", l, re.I)]
print("== euskadi links:", len(links), "hits:", len(hits))
for l in hits[:30]:
    print("   ", l[:170])

# 3) Bizkaia resource page: find API endpoint
h3 = open(r"C:\Users\ELI6-A~1\AppData\Local\Temp\bizk_od.html", encoding="utf-8", errors="replace").read()
links3 = sorted(set(re.findall(r"href=[\"']([^\"']+)[\"']", h3)))
hits3 = [l for l in links3 if re.search(r"json|api|rest|descarg|download|csv|dataset|resource", l, re.I)]
print("== bizkaia links:", len(links3), "hits:", len(hits3))
for l in hits3[:40]:
    print("   ", l[:170])
for m in re.finditer(r"(https?://[^\"' <>]{0,120}(?:api|rest)[^\"' <>]{0,120})", h3):
    print("   API:", m.group(1)[:170])

# 4) Gipuzkoa webcams: images
h4 = open(r"C:\Users\ELI6-A~1\AppData\Local\Temp\gip_webcams.html", encoding="utf-8", errors="replace").read()
imgs4 = sorted(set(re.findall(r"(?:src|data-src|href)=[\"']([^\"']+\.(?:jpg|jpeg|png|gif)[^\"']*)[\"']", h4, re.I)))
print("== gipuzkoa imgs:", len(imgs4))
for i in imgs4[:50]:
    print("   ", i[:170])
t4 = re.search(r"<title>([^<]*)</title>", h4, re.I)
print(" title:", t4.group(1).strip() if t4 else None)
# alt/caption text around images
for m in re.finditer(r"alt=[\"']([^\"']{3,80})[\"']", h4):
    print("   alt:", strip(m.group(1)))
