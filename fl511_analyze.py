"""Analyze fl511 cams data we have so far."""
import json

with open('fl511_cams_all.json') as f:
    data = json.load(f)

cams = data.get('cams', [])
print(f'Total cams: {len(cams):,}')
print(f'Total reported: {data.get("total", "?")}')

# Stats
ids = [c.get('id') for c in cams]
print(f'ID range: {min(ids)} to {max(ids)}')
print(f'Unique IDs: {len(set(ids))}')

# Source breakdown
from collections import Counter
sources = Counter(c.get('source', 'unknown') for c in cams)
print(f'\nTop sources:')
for s, c in sources.most_common(20):
    print(f'  {s}: {c}')

# Regions
regions = Counter(c.get('region', 'unknown') for c in cams)
print(f'\nRegions:')
for r, c in regions.most_common(10):
    print(f'  {r}: {c}')

# Counties
counties = Counter(c.get('county', 'unknown') for c in cams)
print(f'\nTop counties:')
for r, c in counties.most_common(10):
    print(f'  {r}: {c}')

# Has video?
nv = sum(1 for c in cams if c.get('images') and any(im.get('videoUrl') for im in c.get('images', [])))
print(f'\nCams with videoUrl: {nv}')

# imageUrl presence
ni = sum(1 for c in cams if c.get('images') and any(im.get('imageUrl') for im in c.get('images', [])))
print(f'Cams with imageUrl: {ni}')

# Sample 1 cam
print(f'\nSample cam:')
c = cams[0]
for k, v in c.items():
    print(f'  {k}: {str(v)[:200]}')
print(f'  images: {c.get("images")}')
