"""Find divas/m3u8 events."""
import json

with open('fl511_full_trace.json') as f:
    data = json.load(f)
print('=== All divas / m3u8 / video events ===')
for r in data:
    url = r.get('url', '')
    if 'divas' in str(url) or 'm3u8' in str(url) or 'GetVideo' in str(url):
        if 'response' in r:
            print(f'[{r["response"]["status"]}] {url[:200]}')
        else:
            print(f'[{r.get("method")}] {url[:200]}')
