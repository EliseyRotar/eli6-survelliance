"""Refresh Firebase idToken using saved refreshToken."""
import urllib.request
import json
import sys
import socket

socket.setdefaulttimeout(30)

api_key = 'AIzaSyAcfux4lyS-IlYdYMhkxa1u5WRxI9-0RnY'
AUTH_FILE = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_auth.json'

with open(AUTH_FILE) as f:
    auth = json.load(f)
print(f'Old idToken: {auth.get("idToken", "")[:50]}...')
print(f'Old refreshToken: {auth.get("refreshToken", "")[:50]}...')
print(f'localId: {auth.get("localId", "")}')
print(f'email: {auth.get("email", "")}')

# Try refresh
refresh_token = auth.get('refreshToken', '')
url = f'https://securetoken.googleapis.com/v1/token?key={api_key}'
data = f'grant_type=refresh_token&refresh_token={refresh_token}'.encode('utf-8')
req = urllib.request.Request(url, data=data, method='POST', headers={
    'Content-Type': 'application/x-www-form-urlencoded',
})
try:
    r = urllib.request.urlopen(req, timeout=30)
    result = json.loads(r.read())
    print('\nREFRESH OK!')
    new_auth = {
        'kind': 'identitytoolkit#VerifyPasswordResponse',
        'localId': auth['localId'],
        'email': auth['email'],
        'displayName': auth.get('displayName', ''),
        'idToken': result['id_token'],
        'refreshToken': result['refresh_token'],
        'expiresIn': result['expires_in'],
    }
    print(f'New idToken: {result["id_token"][:50]}...')
    with open(AUTH_FILE, 'w') as f:
        json.dump(new_auth, f, indent=2)
    print('Saved to tv_auth.json')
except urllib.error.HTTPError as e:
    body = e.read().decode('utf-8', errors='replace')
    print(f'\nREFRESH FAILED: HTTP {e.code}: {body}')
    print('\nFalling back to full signin...')
    import subprocess
    subprocess.run([sys.executable, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\_tv_signin.py'])
