import urllib.request, socket, json
socket.setdefaulttimeout(60)
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_auth.json') as f:
    auth = json.load(f)
id_token = auth['idToken']

# RTDB REST API uses auth= or Authorization: Bearer
tests = [
    ('https://trafficvision-60eb1-default-rtdb.firebaseio.com/.json?shallow=true', 'no-auth'),
    ('https://trafficvision-60eb1-default-rtdb.firebaseio.com/.json?auth=' + id_token + '&shallow=true', 'auth-query'),
    ('https://trafficvision-60eb1-default-rtdb.firebaseio.com/cameras.json?auth=' + id_token + '&shallow=true', 'cameras'),
    ('https://trafficvision-60eb1-default-rtdb.firebaseio.com/feeds.json?auth=' + id_token + '&shallow=true', 'feeds'),
    ('https://trafficvision-60eb1-default-rtdb.firebaseio.com/sources.json?auth=' + id_token + '&shallow=true', 'sources'),
    ('https://trafficvision-60eb1-default-rtdb.firebaseio.com/users/' + auth['localId'] + '.json?auth=' + id_token, 'user-self'),
    ('https://trafficvision-60eb1-default-rtdb.firebaseio.com/users.json?shallow=true', 'users-shallow'),
]
for u, label in tests:
    try:
        req = urllib.request.Request(u, headers={'Authorization': 'Bearer ' + id_token})
        r = urllib.request.urlopen(req, timeout=30)
        body = r.read()[:1000].decode('utf-8', errors='replace')
        print(f'OK {label}: {r.status} body: {body[:300]}')
    except urllib.error.HTTPError as e:
        body = e.read()[:200].decode('utf-8', errors='replace')
        print(f'ERR {label}: {e.code} {body[:200]}')
    except Exception as e:
        print(f'ERR {label}: {str(e)[:60]}')
