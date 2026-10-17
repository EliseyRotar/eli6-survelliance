# -*- coding: utf-8 -*-
"""Session 47: sitemap parse -> classify URLs."""
import json
import re
from collections import Counter
from urllib.parse import urlparse

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
txt = open(ROOT + r"\_es_camarasdgt_sitemap_index.xml", encoding="utf-8").read()
locs = re.findall(r"<loc>(.*?)</loc>", txt)
print("total urls:", len(locs))

PROV_SLUGS = None  # classify by structure instead
# depth segments after host
segs = [urlparse(u).path.strip("/").split("/") for u in locs]
depth = Counter(len(s) for s in segs)
print("depth dist:", depth)

# roads = 1 segment (road pages) ; province/road = 2; province/road/km = 3 detail
detail = [u for u, s in zip(locs, segs) if len(s) == 3]
roadpage = [u for u, s in zip(locs, segs) if len(s) == 1]
provroad = [u for u, s in zip(locs, segs) if len(s) == 2]
print("detail(3):", len(detail), "prov/road(2):", len(provroad), "road(1):", len(roadpage))

# unique province slugs
provs = Counter(s[0] for s in segs if len(s) >= 2)
print("provinces/roots n:", len(provs))
print(sorted(provs.items(), key=lambda x: -x[1])[:50])

# root-level (1seg) non-road? like avisolegal, blog, buscador
roots = [u for u, s in zip(locs, segs) if len(s) == 1]
print("roots sample:", roots[:40])

open(ROOT + r"\_es_camarasdgt_detail_urls.txt", "w", encoding="utf-8").write("\n".join(detail))
json.dump({"detail": detail, "provroad": provroad, "road": roadpage},
          open(ROOT + r"\_es_camarasdgt_urls.json", "w"), indent=1)
print("saved detail urls:", len(detail))
