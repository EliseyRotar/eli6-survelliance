"""Try to get missing TV shard cbfb074892 via direct HTTP + UA + Referer."""
import urllib.request
import json
import time

url = 'https://api.trafficvision.live/internal/catalog/shards/cbfb074892.json'

# Method 1: plain
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    r = urllib.request.urlopen(req, timeout=10)
    print(f'Method 1: {r.status}, {len(r.read())} bytes')
except Exception as e:
    print(f'Method 1 err: {e}')

# Method 2: with Referer + Origin
try:
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://trafficvision.live/',
        'Origin': 'https://trafficvision.live',
        'Accept': 'application/json, text/plain, */*',
    })
    r = urllib.request.urlopen(req, timeout=10)
    data = r.read()
    print(f'Method 2: {r.status}, {len(data)} bytes')
    if data[:1] == b'{':
        d = json.loads(data)
        if 'cameras' in d:
            print(f'  Cameras: {len(d["cameras"]):,}')
        with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_shards\cbfb074892.json', 'wb') as f:
            f.write(data)
        print('  Saved!')
except Exception as e:
    print(f'Method 2 err: {e}')

# Method 3: with session cookie
try:
    # First get session
    sreq = urllib.request.Request('https://trafficvision.live/', headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64) AppleWebKit/537.36',
    })
    sess = urllib.request.urlopen(sreq, timeout=10)
    cookies = sess.headers.get_all('Set-Cookie')
    print(f'Method 3 session cookies: {cookies}')
    if cookies:
        cookie_str = '; '.join([c.split(';')[0] for c in cookies])
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64) AppleWebKit/537.36',
            'Referer': 'https://trafficvision.live/',
            'Cookie': cookie_str,
        })
        r = urllib.request.urlopen(req, timeout=10)
        data = r.read()
        print(f'  With cookies: {r.status}, {len(data)} bytes')
        if data[:1] == b'{':
            d = json.loads(data)
            if 'cameras' in d:
                print(f'  Cameras: {len(d["cameras"]):,}')
            with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_shards\cbfb074892.json', 'wb') as f:
                f.write(data)
            print('  Saved!')
except Exception as e:
    print(f'Method 3 err: {e}')
