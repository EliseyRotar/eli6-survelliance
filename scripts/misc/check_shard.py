"""Check shard format."""
import json

with open('camera_testing/tv_shards/42dbfe5ace.json', encoding='utf-8') as f:
    d = json.load(f)
print('Type:', type(d).__name__)
if isinstance(d, dict):
    print('Keys:', list(d.keys())[:10])
    for k, v in d.items():
        l = len(v) if hasattr(v, '__len__') else '?'
        print(f'  {k}: type={type(v).__name__} len={l}')
elif isinstance(d, list):
    print('List with', len(d), 'items')
    if d:
        print('First item:', str(d[0])[:300])
