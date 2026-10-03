"""List all shards."""
import json

with open('camera_testing/tv_shards/manifest.json', encoding='utf-8') as f:
    m = json.load(f)
shards = m.get('shards', [])
print(f'Total shards: {len(shards)}')
print()
for s in shards:
    key = s['key']
    cams = s['cameras']
    byts = s['bytes']
    hsh = s['hash']
    print(f'  {key:40s} {cams:>7,} cams, {byts:>10,} bytes, hash={hsh}')

# Also check files on disk
import os
disk = []
for f in os.listdir('camera_testing/tv_shards'):
    if f.endswith('.json') and f != 'manifest.json' and f != 'manifest-e5d25aea.js':
        disk.append(f.replace('.json', ''))
print(f'\nOn disk: {len(disk)} shards')
print(f'  {disk}')
