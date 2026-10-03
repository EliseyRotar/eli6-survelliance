"""Check manifest."""
import json

with open('camera_testing/tv_shards/manifest.json', encoding='utf-8') as f:
    m = json.load(f)
print('Top-level keys:', list(m.keys()))
print('version:', m.get('version'))
print('totalCameras:', m.get('totalCameras'))
if 'shards' in m:
    print('shards:', len(m['shards']))
    print('first 3 shards:')
    for s in m['shards'][:3]:
        print(f'  {s}')
if 'catalog' in m:
    print('catalog:', list(m['catalog'].keys())[:20])
