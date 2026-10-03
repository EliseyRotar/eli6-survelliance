import urllib.request, socket, json
socket.setdefaulttimeout(60)
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_auth.json') as f:
    auth = json.load(f)
id_token = auth['idToken']

# api.trafficvision.live endpoints with auth
tests = [
    ('https://api.trafficvision.live/v1/cameras?pageSize=5', 'cameras'),
    ('https://api.trafficvision.live/v1/feeds', 'feeds'),
    ('https://api.trafficvision.live/v1/sources', 'sources'),
    ('https://api.trafficvision.live/v1/manifest', 'manifest'),
    ('https://api.trafficvision.live/v1/catalog', 'catalog'),
    ('https://api.trafficvision.live/v1/catalogues', 'catalogues'),
    ('https://api.trafficvision.live/v1/index.json', 'index'),
    ('https://api.trafficvision.live/v1/caltrans-cameras.json', 'caltrans-cams'),
    ('https://api.trafficvision.live/v1/argus-cameras.json', 'argus-cams'),
    ('https://api.trafficvision.live/v1/erau-cameras.json', 'erau-cams'),
    ('https://api.trafficvision.live/v1/insecam-cameras.json', 'insecam-cams'),
    ('https://api.trafficvision.live/v1/me', 'me'),
    ('https://api.trafficvision.live/v1/user', 'user'),
    ('https://api.trafficvision.live/v1/users/me', 'users-me'),
    ('https://api.trafficvision.live/v1/premium', 'premium'),
    ('https://api.trafficvision.live/v1/data.json', 'data'),
]
for u, label in tests:
    try:
        req = urllib.request.Request(u, headers={
            'Authorization': 'Bearer ' + id_token,
            'Accept': 'application/json',
        })
        r = urllib.request.urlopen(req, timeout=30)
        body = r.read()[:1500].decode('utf-8', errors='replace')
        print(f'OK {label}: {r.status}')
        print(f'  body: {body[:500]}')
    except urllib.error.HTTPError as e:
        body = e.read()[:200].decode('utf-8', errors='replace')
        print(f'ERR {label}: {e.code} {body[:150]}')
    except Exception as e:
        print(f'ERR {label}: {str(e)[:60]}')
