"""Show all m3u8 URLs."""
import json

with open('fl511_video_url_flow.json') as f:
    data = json.load(f)
print('All m3u8 URLs:')
for d in data:
    if '.m3u8' in d.get('url', ''):
        print(f'  {d["url"]}')
