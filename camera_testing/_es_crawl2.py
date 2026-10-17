# -*- coding: utf-8 -*-
"""Session 47: crawl listing pages (prov/road + webcam + andorra) for image universe."""
import json
import re
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

urls = json.load(open(ROOT + r"\_es_camarasdgt_urls.json", encoding="utf-8"))
targets = list(dict.fromkeys(urls["provroad"] + urls["road"]))
# plus andorra subtree + webcam root from sitemap
txt = open(ROOT + r"\_es_camarasdgt_sitemap_index.xml", encoding="utf-8").read()
locs = re.findall(r"<loc>(.*?)</loc>", txt)
for u in locs:
    segs = urlparse(u).path.strip("/").split("/")
    if segs and segs[0] in ("andorra", "webcam") and len(segs) <= 3:
        targets.append(u)
targets = list(dict.fromkeys(targets))
print("listing targets:", len(targets), flush=True)


def grab(u, tries=2):
    for i in range(tries):
        req = urllib.request.Request(u, headers=UA)
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read(300000)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if i == tries - 1:
                return None
            time.sleep(1.5)
        except Exception:
            if i == tries - 1:
                return None
            time.sleep(1.5)
    return None


results = {}
errs = 0
t0 = time.time()


def work(u):
    b = grab(u)
    if b is None:
        return u, None
    html = b.decode("utf-8", "replace")
    imgs = re.findall(r"<img[^>]*?src=[\"']([^\"']+)[\"'][^>]*?>", html, re.I)
    cam_imgs = []
    for t in imgs:
        if re.search(r"favicon|logo|icon|banner|placeholder|loading\.gif|google", t, re.I):
            continue
        cam_imgs.append(t)
    # h1s + img titles give labels per cam
    titles = re.findall(r'<img[^>]*title="([^"]*)"', html, re.I)
    alts = re.findall(r'<img[^>]*alt="([^"]*)"', html, re.I)
    return u, {"imgs": cam_imgs, "titles": titles, "alts": alts, "size": len(b)}


with ThreadPoolExecutor(max_workers=6) as ex:
    futs = [ex.submit(work, u) for u in targets]
    for i, f in enumerate(as_completed(futs), 1):
        u, rec = f.result()
        if rec:
            results[u] = rec
        else:
            errs += 1
        if i % 100 == 0:
            print(f"  {i}/{len(targets)} ok={len(results)} err={errs} {time.time()-t0:.0f}s", flush=True)

json.dump(results, open(ROOT + r"\_es_camarasdgt_listings.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("done:", len(results), "errs:", errs, f"{time.time()-t0:.0f}s", flush=True)

etraffic_ids = set()
external = {}
for u, rec in results.items():
    for img in rec["imgs"]:
        m = re.search(r"camarasEtraffic/(\d+)\.jpg", img)
        if m:
            etraffic_ids.add(m.group(1))
        elif re.search(r"\.(jpg|jpeg|png|gif|webp)", img, re.I):
            external.setdefault(img, set()).add(u)
known = set()
prod = json.load(open(ROOT + r"\_es_camaras_etraffic.json", encoding="utf-8"))["camaras"]
known |= {c["idCamara"] for c in prod}
extras = {"993", "168856", "176531", "176532", "176533", "176534", "176535", "176537",
          "178574", "181921", "181924", "18", "103", "1040"}
known |= extras
print("etraffic ids in listings:", len(etraffic_ids))
new_ids = sorted(etraffic_ids - known, key=int)
print("NEW etraffic ids:", len(new_ids), new_ids[:60])
print("external urls:", len(external))
for k in sorted(external):
    print("  ", k, "| pages:", len(external[k]), "| e.g.", list(external[k])[0])
