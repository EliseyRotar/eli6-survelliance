#!/usr/bin/env python3
import urllib.request
import ssl
import json
import sys

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = 'https://195.196.36.242/axis-cgi/apidiscovery.cgi'
data = json.dumps({'apiVersion': '1.0', 'method': 'getApiList'}).encode('utf-8')
req = urllib.request.Request(url, data=data, method='POST',
                             headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
    body = r.read().decode('utf-8', errors='replace')
    j = json.loads(body)
    print('AXIS VAPIX API endpoints on this device:')
    for a in j['data']['apiList']:
        api_id = a.get('id')
        version = a.get('version')
        name = a.get('name')
        print(f'  [{api_id}] {name} v{version}')
    print()
    # Save full response
    open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\axis_api_list.json', 'w').write(body)
    print(f'Saved {len(body)} bytes to axis_api_list.json')