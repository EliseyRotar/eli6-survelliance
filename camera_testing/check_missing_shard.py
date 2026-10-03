"""Try to get the missing TV shard 12 (cbfb074892) via various methods."""
import urllib.request
import json
import time
import os

# Load manifest
manifest_path = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_shards\manifest.json'
with open(manifest_path) as f:
    m = json.load(f)

print(f'Manifest: version={m.get("version")}, total={m.get("totalCameras"):,}')
print(f'Shards: {len(m["shards"])}')

for s in m['shards']:
    print(f'  {s["id"]}.json: {s.get("cameraCount", "?")} cams')

# Find the missing one
present = {s['id'] for s in m['shards']}
all_ids = [s['id'] for s in m['shards']]
missing = []
print(f'All {len(present)} shard IDs:', present)
