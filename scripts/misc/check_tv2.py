"""Check TV catalog structure."""
import json
from collections import Counter

with open('camera_testing/tv_catalog_full.json') as f:
    catalog = json.load(f)
cams = catalog['cameras']

srcs = Counter(c.get('source', 'none') for c in cams)
print('Top 30 sources:')
for s, c in srcs.most_common(30):
    print(f'  {s}: {c}')

nv = sum(1 for c in cams if c.get('videoUrl'))
ni = sum(1 for c in cams if c.get('imageUrl'))
ny = sum(1 for c in cams if c.get('youtubeVideoId'))
na = sum(1 for c in cams if c.get('angles'))
nipc = sum(1 for c in cams if c.get('ipcamliveAlias'))
ns = sum(1 for c in cams if c.get('sourceUrl'))
print(f'\nvideoUrl: {nv}')
print(f'imageUrl: {ni}')
print(f'youtubeVideoId: {ny}')
print(f'angles: {na}')
print(f'ipcamliveAlias: {nipc}')
print(f'sourceUrl: {ns}')

print('\nSamples:')
for i in [0, 100, 1000, 10000, 50000, 80000, 100000, 120000, 140000]:
    if i < len(cams):
        c = cams[i]
        cid = c.get('id', '')
        src = c.get('source', '')
        vu = (c.get('videoUrl') or '')[:50]
        iu = (c.get('imageUrl') or '')[:50]
        print(f'  [{i}] {cid} | {src} | V={vu} | I={iu}')
