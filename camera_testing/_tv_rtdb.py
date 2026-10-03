import urllib.request, socket, json
socket.setdefaulttimeout(30)
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_auth.json') as f:
    auth = json.load(f)
id_token = auth['idToken']
# RTDB with auth
url = 'https://trafficvision-60eb1-default-rtdb.firebaseio.com/.json?auth=' + id_token + '&shallow=true'
req = urllib.request.Request(url)
try:
    r = urllib.request.urlopen(req, timeout=30)
    body = r.read().decode('utf-8', errors='replace')
    print(f'OK shallow=true: {r.status}')
    keys = list(json.loads(body).keys())
    print(f'top-level keys ({len(keys)}):')
    for k in keys[:50]:
        print(f'  {k}')
except urllib.error.HTTPError as e:
    body = e.read().decode('utf-8', errors='replace')
    print(f'ERR shallow: {e.code} {body[:300]}')
except Exception as e:
    print(f'ERR: {e}')
