import urllib.request, socket, json
socket.setdefaulttimeout(30)
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_auth.json') as f:
    auth = json.load(f)
id_token = auth['idToken']

# Get session from /api/session
urls = [
    'https://app.trafficvision.live/api/session',
    'https://app.trafficvision.live/api/me',
    'https://app.trafficvision.live/api/511ga',
    'https://app.trafficvision.live/api/njhls',
    'https://app.trafficvision.live/api/kandrive',
    'https://app.trafficvision.live/api/drivenc',
    'https://app.trafficvision.live/api/biysk',
]
for u in urls:
    try:
        req = urllib.request.Request(u, headers={
            'Authorization': f'Bearer {id_token}',
            'Accept': 'application/json',
        })
        r = urllib.request.urlopen(req, timeout=15)
        body = r.read()[:500].decode('utf-8', errors='replace')
        print(f'OK {u}: {r.status}')
        print(f'  body: {body[:300]}')
    except urllib.error.HTTPError as e:
        body = e.read()[:200].decode('utf-8', errors='replace')
        print(f'ERR {u}: {e.code} {body[:150]}')
    except Exception as e:
        print(f'ERR {u}: {str(e)[:60]}')
