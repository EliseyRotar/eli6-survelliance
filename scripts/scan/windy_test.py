"""Test Windy API for Ruse cams."""
import urllib.request
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

for wid in [1597690315, 1793898215, 1793902097]:
    print(f'\n=== Windy cam {wid} ===')
    for ep in [
        f'https://node.windy.com/webcams/api/v3/webcams/{wid}',
        f'https://webcams.windy.com/api/v3/webcams/{wid}',
        f'https://node.windy.com/webcams/api/webcam/{wid}',
    ]:
        try:
            req = urllib.request.Request(ep, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5, context=ctx) as r:
                data = r.read()
                ct = r.headers.get('Content-Type', '')
                print(f'  {ep}: {r.status} {ct} {len(data)} bytes')
                if 'json' in ct and len(data) > 100:
                    d = json.loads(data)
                    keys = list(d.keys())[:10]
                    print(f'    Keys: {keys}')
                    if 'player' in d:
                        print(f'    Player: {d["player"]}')
                    if 'image' in d:
                        img = d['image']
                        if isinstance(img, dict):
                            print(f'    Image: {list(img.keys())[:5]}')
                            if 'current' in img:
                                print(f'    Current: {list(img["current"].keys())[:5]}')
                    if 'videos' in d:
                        print(f'    Videos: {d["videos"]}')
                    if 'live' in d:
                        print(f'    Live: {d["live"]}')
        except urllib.error.HTTPError as e:
            print(f'  {ep}: HTTP {e.code}')
        except Exception as e:
            print(f'  {ep}: {e}')
