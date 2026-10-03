import urllib.request, socket, json
socket.setdefaulttimeout(30)
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_auth.json') as f:
    auth = json.load(f)
id_token = auth['idToken']
local_id = auth['localId']
urls = [
    'https://firestore.googleapis.com/v1/projects/trafficvision-60eb1/databases/(default)/documents/cameras?pageSize=5',
    'https://firestore.googleapis.com/v1/projects/trafficvision-60eb1/databases/(default)/documents/cams?pageSize=5',
    'https://firestore.googleapis.com/v1/projects/trafficvision-60eb1/databases/(default)/documents/feeds?pageSize=5',
    'https://firestore.googleapis.com/v1/projects/trafficvision-60eb1/databases/(default)/documents/users/' + local_id,
    'https://firestore.googleapis.com/v1/projects/trafficvision-60eb1/databases/(default)/documents/users?pageSize=5',
    'https://firestore.googleapis.com/v1/projects/trafficvision-60eb1/databases/(default)/documents/catalog?pageSize=5',
    'https://firestore.googleapis.com/v1/projects/trafficvision-60eb1/databases/(default)/documents/catalogues?pageSize=5',
    'https://firestore.googleapis.com/v1/projects/trafficvision-60eb1/databases/(default)/documents:runQuery',
    'https://firestore.googleapis.com/v1/projects/trafficvision-60eb1/databases/(default)/documents/cameras/argus?pageSize=5',
    'https://firestore.googleapis.com/v1/projects/trafficvision-60eb1/databases/(default)/documents/cameras/caltrans?pageSize=5',
    'https://firestore.googleapis.com/v1/projects/trafficvision-60eb1/databases/(default)/documents/sources?pageSize=5',
]
for u in urls:
    try:
        req = urllib.request.Request(u, headers={
            'Authorization': f'Bearer {id_token}',
            'Content-Type': 'application/json',
        })
        r = urllib.request.urlopen(req, timeout=10)
        body = r.read()[:500].decode('utf-8', errors='replace')
        print(f'OK {u[:90]}: {r.status}')
        print(f'  body: {body[:300]}')
    except urllib.error.HTTPError as e:
        body = e.read()[:200].decode('utf-8', errors='replace')
        print(f'ERR {u[:90]}: {e.code} {body[:200]}')
    except Exception as e:
        print(f'ERR {u[:90]}: {str(e)[:60]}')
