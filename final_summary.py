"""Final status summary."""
import json
import time
import os
import re
import csv
from collections import Counter

print('=== FL511 (Florida DOT) ===')
with open('fl511_cams_all.json') as f:
    d = json.load(f)
cams = d['cams']
nv = sum(1 for c in cams if c.get('images') and any(im.get('videoUrl') for im in c.get('images', [])))
print(f'  Got: {len(cams):,} cams (out of {d["total"]:,} total)')
print(f'  With videoUrl field: {nv:,}')
print(f'  Need /Camera/GetVideoUrl for: {len(cams) - nv:,} more (have isVideoAuthRequired)')

print()
print('=== TrafficVision.Live ===')
p = 'camera_testing/tv_catalog_full.json'
mtime = time.ctime(os.path.getmtime(p))
with open(p) as f:
    d = json.load(f)
cams = d['cameras']
print(f'  Catalog: {len(cams):,} cams (file mtime: {mtime})')
print(f'  Site claims: 155,000+ cams')
print(f'  Gap: ~6,500 cams potentially missing in our catalog')

# In CSV
csv.field_size_limit(2**31 - 1)
n_tv = 0
sources = Counter()
with open('controllable_Webcams.csv', 'r', encoding='utf-8', errors='replace') as f:
    for row in csv.DictReader(f):
        notes = row.get('notes', '') or ''
        if 'trafficvision_id' in notes:
            n_tv += 1
            m = re.search(r'trafficvision_id=([^:;]+):', notes)
            if m:
                sources[m.group(1)] += 1
print(f'  In CSV with trafficvision_id: {n_tv:,}')
print(f'  Top sources in CSV:')
for s, c in sources.most_common(20):
    print(f'    {s}: {c}')
