"""Login to trafficvision.live via headless browser to get cookies.

Uses urllib + manual flow:
1. GET /auth/signin -> get csrf token (if any)
2. POST email/password via Firebase REST (we already did this)
3. Use idToken to access TV endpoints with proper browser fingerprint
"""
import urllib.request, urllib.parse, json, http.cookiejar, sys, time, socket
socket.setdefaulttimeout(30)

EMAIL = 'fohot18565@kolsea.com'
PASSWORD = 'Tp?kKD)Y>ya5:s%'
API_KEY = 'AIzaSyAcfux4lyS-IlYdYMhkxa1u5WRxI9-0RnY'

# Step 1: signin via Identity Toolkit REST
url = f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}'
data = json.dumps({
    'email': EMAIL,
    'password': PASSWORD,
    'returnSecureToken': True,
}).encode('utf-8')
req = urllib.request.Request(url, data=data, method='POST', headers={
    'Content-Type': 'application/json',
})
r = urllib.request.urlopen(req, timeout=30)
auth = json.loads(r.read())
print('Signed in. localId:', auth['localId'])

# Step 2: exchange idToken for TV session cookie
# This is what the browser does when Firebase Auth signs in.
# The TV app then has the user's session and can access Firestore/RTDB via auth.

# Save idToken + refresh
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_auth.json', 'w') as f:
    json.dump(auth, f, indent=2)

# Try to use it to fetch data from Firestore (we proved this works for users collection)
# The real question is: how does the SPA get the 155k cams?

# Let me look at what calls the SPA makes. Maybe via gRPC/webchannel.
# Firestore gRPC REST proxy:
# https://firestore.googleapis.com/v1/projects/{project}/databases/(default)/documents:batchGet
# https://firestore.googleapis.com/v1/projects/{project}/databases/(default)/documents/{path}:listen

# Try the listen endpoint to see what it returns
listen_urls = [
    f'https://firestore.googleapis.com/v1/projects/trafficvision-60eb1/databases/(default)/documents/cameras:listen',
    f'https://firestore.googleapis.com/v1/projects/trafficvision-60eb1/databases/(default)/documents:listen',
    f'https://firestore.googleapis.com/v1/projects/trafficvision-60eb1/databases/(default)/documents/catalog:listen',
    f'https://firestore.googleapis.com/v1/projects/trafficvision-60eb1/databases/(default)/documents/catalogues:listen',
]
for u in listen_urls:
    try:
        req = urllib.request.Request(u, method='POST', headers={
            'Authorization': f'Bearer {auth["idToken"]}',
            'Content-Type': 'application/json',
        })
        r = urllib.request.urlopen(req, timeout=15)
        body = r.read()[:300].decode('utf-8', errors='replace')
        print(f'OK {u}: {r.status} {body[:200]}')
    except urllib.error.HTTPError as e:
        body = e.read()[:200].decode('utf-8', errors='replace')
        print(f'ERR {u}: {e.code} {body[:150]}')
    except Exception as e:
        print(f'ERR {u}: {str(e)[:80]}')
