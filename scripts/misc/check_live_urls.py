"""Check live URLs captured."""
import json

with open('fl511_live_progress.json', encoding='utf-8') as f:
    d = json.load(f)
queried = d.get('queried', {})
print(f'Queried: {len(queried):,}')
n_with_url = sum(1 for v in queried.values() if v.get('video_url'))
print(f'With video_url: {n_with_url:,}')
# Show one example
for k, v in list(queried.items())[:3]:
    url = v.get('video_url', '') or 'no url'
    print(f'  {k}: {url[:80]}')
    print(f'    result keys: {list(v.get("result", {}).keys())}')
    print(f'    result: {v.get("result", {})}')
