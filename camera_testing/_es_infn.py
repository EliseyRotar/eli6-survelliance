# -*- coding: utf-8 -*-
"""Extract espalet (and other) cam titles + image URLs from infonieve Formigal page."""
import re
import io
import os

p = os.environ["TEMP"] + r"\infonieve_formigal.html"
h = io.open(p, encoding="utf-8", errors="replace").read()

# split into cam boxes
boxes = re.split(r'box_listhistocams(?:_item)?["\']', h)
print("boxes:", len(boxes) - 1)
for b in boxes[1:]:
    t = re.search(r'box_listhistocams_title[^>]*>\s*(?:<[^>]+>\s*)*([^<]{2,90})<', b)
    img = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', b)
    author = re.search(r'track_([^_]+(?:-[^_]+)*)_', b)
    title = t.group(1).strip() if t else "?"
    print("TITLE:", title)
    if img:
        print("   IMG:", img.group(1))
