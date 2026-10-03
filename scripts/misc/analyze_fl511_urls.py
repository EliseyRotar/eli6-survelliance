"""Analyze fl511 cams with vs without videoUrl."""
import json
import re
from collections import Counter

with open('fl511_cams_all.json') as f:
    data = json.load(f)
cams = data.get('cams', [])

with_url = 0
without_url = 0
url_patterns = Counter()
servers = Counter()

for c in cams:
    images = c.get('images') or []
    if not images:
        continue
    img = images[0]
    vu = img.get('videoUrl', '')
    if vu:
        with_url += 1
        m = re.match(r'(https?://([^/]+))', vu)
        if m:
            servers[m.group(1)] += 1
        m2 = re.search(r'/chan-(\d+)_', vu)
        if m2:
            url_patterns[f'chan-{m2.group(1)}_h'] += 1
    else:
        without_url += 1

print(f'Cams with videoUrl: {with_url:,}')
print(f'Cams without: {without_url:,}')
print(f'\nTop divas servers:')
for s, c in servers.most_common(10):
    print(f'  {s}: {c}')
print(f'\nChan patterns (first 20):')
for p, c in url_patterns.most_common(20):
    print(f'  {p}: {c}')

# Sample cams WITHOUT videoUrl
print(f'\nSample cams WITHOUT videoUrl:')
count = 0
for c in cams:
    images = c.get('images') or []
    if not images:
        continue
    img = images[0]
    if not img.get('videoUrl'):
        if count < 10:
            print(f'  {c.get("id")}: sourceId={c.get("sourceId")} | isVideoAuthRequired={img.get("isVideoAuthRequired")}')
            count += 1
