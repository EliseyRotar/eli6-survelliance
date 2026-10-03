"""Try to get shard via manifest -> session chain."""
import urllib.request
import urllib.error
import json
import time
import http.cookiejar

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(cj),
    urllib.request.HTTPRedirectHandler()
)

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Step 1: Visit main page
print('Step 1: GET /')
try:
    r = opener.open('https://trafficvision.live/', timeout=10)
    print(f'  Status: {r.status}, len: {len(r.read())}')
    print(f'  Cookies: {[c.name for c in cj]}')
except Exception as e:
    print(f'  err: {e}')

# Step 2: Get manifest
print('\nStep 2: GET /internal/manifest')
try:
    req = urllib.request.Request('https://api.trafficvision.live/internal/manifest', headers={
        'User-Agent': UA,
        'Referer': 'https://trafficvision.live/',
        'Origin': 'https://trafficvision.live',
        'Accept': 'application/json, text/plain, */*',
    })
    r = opener.open(req, timeout=10)
    data = r.read()
    print(f'  Status: {r.status}, len: {len(data)}')
    print(f'  Cookies: {[c.name for c in cj]}')
except Exception as e:
    print(f'  err: {e}')

# Step 3: Now try shard
print('\nStep 3: GET /internal/catalog/shards/cbfb074892.json')
try:
    req = urllib.request.Request(
        'https://api.trafficvision.live/internal/catalog/shards/cbfb074892.json',
        headers={
            'User-Agent': UA,
            'Referer': 'https://trafficvision.live/',
            'Origin': 'https://trafficvision.live',
            'Accept': 'application/json, text/plain, */*',
        }
    )
    r = opener.open(req, timeout=10)
    data = r.read()
    print(f'  Status: {r.status}, len: {len(data)}')
    if data[:1] == b'{':
        d = json.loads(data)
        if 'cameras' in d:
            print(f'  Cameras: {len(d["cameras"]):,}')
        with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_shards\cbfb074892.json', 'wb') as f:
            f.write(data)
        print('  Saved!')
except Exception as e:
    print(f'  err: {e}')
