import json
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_shards\manifest', encoding='utf-8') as f:
    data = json.load(f)
print('total shards:', len(data.get('shards', [])))
total = 0
for s in data.get('shards', []):
    total += s.get('cameras', 0)
    key = s['key']
    cams = s['cameras']
    sz = s['bytes']
    h = s['hash']
    print(f'  {key}: {cams} cams, {sz} bytes, hash={h}')
print(f'TOTAL cams from shards: {total}')
print(f'TOTAL reported in manifest: {data["totalCameras"]}')
print(f'Excluded sources: {data["excludedSources"]}')
