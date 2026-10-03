import json

with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_shards\manifest.json', encoding='utf-8') as f:
    m = json.load(f)

print('Total:', m.get('totalCameras'), 'shards:', len(m['shards']))
import os
for s in m['shards']:
    fn = os.path.basename(s['key'])
    path = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_shards' + '\\' + fn
    exists = os.path.exists(path)
    print(f'  {fn}: {s.get("cameras", 0):,} cams {"OK" if exists else "MISSING"}')
