import urllib.request, socket, json
socket.setdefaulttimeout(30)
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_auth.json') as f:
    auth = json.load(f)
id_token = auth['idToken']

# Firestore REST batchGet
test_urls = [
    # List collections (need document path)
    ('https://firestore.googleapis.com/v1/projects/trafficvision-60eb1/databases/(default)/documents/cameras', 'list-cameras'),
    ('https://firestore.googleapis.com/v1/projects/trafficvision-60eb1/databases/(default)/documents/users/OtaMfcZTTBYdE2JxCksRQlue7EW2/favorites', 'user-favorites'),
    ('https://firestore.googleapis.com/v1/projects/trafficvision-60eb1/databases/(default)/documents/users/OtaMfcZTTBYdE2JxCksRQlue7EW2/bookmarks', 'user-bookmarks'),
    ('https://firestore.googleapis.com/v1/projects/trafficvision-60eb1/databases/(default)/documents/users/OtaMfcZTTBYdE2JxCksRQlue7EW2/routes', 'user-routes'),
    ('https://firestore.googleapis.com/v1/projects/trafficvision-60eb1/databases/(default)/documents/users/OtaMfcZTTBYdE2JxCksRQlue7EW2/collections', 'user-collections'),
    ('https://firestore.googleapis.com/v1/projects/trafficvision-60eb1/databases/(default)/documents/users/OtaMfcZTTBYdE2JxCksRQlue7EW2/previewStatus', 'user-preview'),
    # List user subcollections
    ('https://firestore.googleapis.com/v1/projects/trafficvision-60eb1/databases/(default)/documents/users/OtaMfcZTTBYdE2JxCksRQlue7EW2?mask.fieldPaths=name', 'user-doc'),
]
for u, label in test_urls:
    try:
        req = urllib.request.Request(u, headers={
            'Authorization': f'Bearer {id_token}',
            'Content-Type': 'application/json',
        })
        r = urllib.request.urlopen(req, timeout=15)
        body = r.read()[:500].decode('utf-8', errors='replace')
        print(f'OK {label}: {r.status}')
        print(f'  body: {body[:300]}')
    except urllib.error.HTTPError as e:
        body = e.read()[:200].decode('utf-8', errors='replace')
        print(f'ERR {label}: {e.code} {body[:150]}')
    except Exception as e:
        print(f'ERR {label}: {str(e)[:60]}')
