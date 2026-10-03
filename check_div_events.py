"""Find divas events."""
import json
with open('fl511_video_div.json') as f:
    data = json.load(f)
for e in data:
    url = e.get('url', '')
    if 'divas' in url or 'm3u8' in url:
        if e.get('type') == 'request':
            m = e.get('method', '?')
            u = url[:200]
            print(f'[{m}] {u}')
        else:
            s = e.get('status', '?')
            u = url[:200]
            b = e.get('body', '')[:200]
            print(f'[{s}] {u} body: {b}')
