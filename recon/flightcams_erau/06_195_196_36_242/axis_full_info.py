#!/usr/bin/env python3
import urllib.request
import ssl
import json
import sys

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Helper
def post(url, payload, timeout=10):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST',
                                 headers={'Content-Type': 'application/json',
                                          'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return json.loads(r.read().decode('utf-8', errors='replace'))

# 1. Basic device info
print("=" * 60)
print("Basic Device Info (model, firmware, serial, etc.)")
print("=" * 60)
try:
    j = post('https://195.196.36.242/axis-cgi/basicdeviceinfo.cgi',
             {'apiVersion': '1.0', 'method': 'getAllProperties'})
    print(json.dumps(j, indent=2)[:3000])
    open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\axis_deviceinfo.json', 'w').write(json.dumps(j, indent=2))
except Exception as e:
    print(f"err: {e}")

# 2. Stream profiles (the actual stream URLs!)
print()
print("=" * 60)
print("Stream Profiles")
print("=" * 60)
try:
    j = post('https://195.196.36.242/axis-cgi/streamprofile.cgi',
             {'apiVersion': '1.0', 'method': 'getAllStreamProfiles'})
    print(json.dumps(j, indent=2)[:3000])
    open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\axis_streams.json', 'w').write(json.dumps(j, indent=2))
except Exception as e:
    print(f"err: {e}")

# 3. Try the legacy param.cgi to get model
print()
print("=" * 60)
print("Legacy param.cgi (CGI)")
print("=" * 60)
try:
    req = urllib.request.Request('https://195.196.36.242/axis-cgi/param.cgi?action=list',
                                 headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
        body = r.read().decode('utf-8', errors='replace')
        print(body[:3000])
        open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\axis_params.txt', 'w').write(body)
except Exception as e:
    print(f"err: {e}")

# 4. Image size
print()
print("=" * 60)
print("Image sizes supported")
print("=" * 60)
try:
    j = post('https://195.196.36.242/axis-cgi/imagesize.cgi',
             {'apiVersion': '1.0', 'method': 'getCapabilities'})
    print(json.dumps(j, indent=2)[:2000])
except Exception as e:
    print(f"err: {e}")