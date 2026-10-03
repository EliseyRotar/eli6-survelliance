"""Extract all captured trafficvision.live catalog shards to a single JSON."""
import json
import os

CAPTURED = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_captured.json'
OUTPUT = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_catalog_full.json'
SHARDS_DIR = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_shards'

os.makedirs(SHARDS_DIR, exist_ok=True)

with open(CAPTURED) as f:
    data = json.load(f)

# Filter for catalog shards
shards = []
manifests = []
for r in data:
    url = r['url']
    body = r['body']
    if '/catalog/shards/' in url:
        # Save shard
        shard_id = url.split('/')[-1]
        path = os.path.join(SHARDS_DIR, shard_id)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(body)
        shards.append({'url': url, 'file': path, 'size': len(body)})
    elif '/manifest' in url:
        path = os.path.join(SHARDS_DIR, 'manifest.json')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(body)
        manifests.append({'url': url, 'file': path, 'size': len(body)})

print(f'shards saved: {len(shards)}')
print(f'manifests saved: {len(manifests)}')

# Parse and merge all cameras
all_cameras = []
for shard_info in shards:
    with open(shard_info['file']) as f:
        try:
            data = json.loads(f.read())
        except Exception as e:
            print(f'parse err {shard_info["file"]}: {e}')
            continue
    cams = data.get('cameras', [])
    all_cameras.extend(cams)
    print(f'  {shard_info["file"].split(chr(92))[-1]}: {len(cams)} cams')

print(f'\nTOTAL cameras: {len(all_cameras)}')

# Save merged catalog
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump({'cameras': all_cameras}, f, indent=2)
print(f'Saved to {OUTPUT}')
