"""Firebase Auth sign-in via REST API for trafficvision.live."""
import urllib.request
import urllib.parse
import json
import sys
import socket

socket.setdefaulttimeout(30)

api_key = 'AIzaSyAcfux4lyS-IlYdYMhkxa1u5WRxI9-0RnY'
project_id = 'trafficvision-60eb1'

email = sys.argv[1] if len(sys.argv) > 1 else 'fohot18565@kolsea.com'
password = sys.argv[2] if len(sys.argv) > 2 else 'Tp?kKD)Y>ya5:s%'

# signInWithPassword endpoint
url = f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}'
data = json.dumps({
    'email': email,
    'password': password,
    'returnSecureToken': True,
}).encode('utf-8')
req = urllib.request.Request(url, data=data, method='POST', headers={
    'Content-Type': 'application/json',
})
try:
    r = urllib.request.urlopen(req, timeout=30)
    result = json.loads(r.read())
    print('OK!')
    print('idToken:', result.get('idToken', '')[:80] + '...')
    print('refreshToken:', result.get('refreshToken', '')[:80] + '...')
    print('localId:', result.get('localId', ''))
    print('email:', result.get('email', ''))
    print('expiresIn:', result.get('expiresIn', ''))
    # Save token
    with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_auth.json', 'w') as f:
        json.dump(result, f, indent=2)
    print('Saved to tv_auth.json')
except urllib.error.HTTPError as e:
    body = e.read().decode('utf-8', errors='replace')
    print(f'HTTP {e.code}: {body}')
    if 'INVALID_PASSWORD' in body:
        print('Wrong password')
    elif 'USER_NOT_FOUND' in body:
        print('User does not exist')
    elif 'TOO_MANY_ATTEMPTS' in body:
        print('Rate limited')
    elif 'API_KEY_INVALID' in body:
        print('API key wrong')
    elif 'OPERATION_NOT_ALLOWED' in body:
        print('Email/password signin not enabled')
