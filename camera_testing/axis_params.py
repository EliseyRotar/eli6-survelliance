#!/usr/bin/env python3
import urllib.request
import ssl
import json
import sys
import re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Get all params
req = urllib.request.Request('https://195.196.36.242/axis-cgi/param.cgi?action=list',
                             headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
    body = r.read().decode('utf-8', errors='replace')

# Save full
open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\axis_params_full.txt', 'w').write(body)

# Parse and find stream-related params
print("=" * 60)
print("Stream-related params")
print("=" * 60)
for line in body.split('\n'):
    if 'tream' in line.lower() or 'ideo' in line.lower() or 'ideoCompression' in line.lower() or 'H264' in line or 'zipstream' in line.lower():
        if 'AudioSource' not in line and 'Image.I0' not in line[:20]:
            print(f"  {line[:200]}")

print()
print("=" * 60)
print("Image I0 stream config")
print("=" * 60)
for line in body.split('\n'):
    if 'Image.I0' in line and 'Stream' in line:
        print(f"  {line[:200]}")

print()
print("=" * 60)
print("All H264 settings")
print("=" * 60)
for line in body.split('\n'):
    if 'H264' in line or 'h264' in line or 'MP4' in line or 'Mpeg4' in line:
        print(f"  {line[:200]}")

print()
print("=" * 60)
print("Stream profile names")
print("=" * 60)
for line in body.split('\n'):
    if 'treamProfile' in line or 'profile.Name' in line:
        print(f"  {line[:200]}")

print()
print("=" * 60)
print("Source (camera sensor)")
print("=" * 60)
for line in body.split('\n'):
    if 'VideoSource' in line or 'Source.NbrOf' in line:
        print(f"  {line[:200]}")

# Also try image config
print()
print("=" * 60)
print("Trying MJPEG/H264 endpoints")
print("=" * 60)
endpoints = [
    'https://195.196.36.242/axis-cgi/mjpg/video.cgi',
    'https://195.196.36.242/axis-cgi/mjpg/video.cgi?camera=1',
    'https://195.196.36.242/axis-cgi/mjpg/video.cgi?camera=1&resolution=1920x1080',
    'https://195.196.36.242/axis-cgi/media-cgi?action=getmjpeg&camera=1',
    'https://195.196.36.242/axis-cgi/media/image.cgi?camera=1&resolution=1920x1080',
    'https://195.196.36.242/axis-cgi/media/image.cgi?camera=1',
    'https://195.196.36.242/axis-cgi/mediastream.cgi?action=start&camera=1',
    'https://195.196.36.242/axis-cgi/mediastream.cgi',
    'https://195.196.36.242/local/mediastream.cgi',
    'https://195.196.36.242/axis-cgi/mediastream.cgi?camera=1&streamprofile=high',
    'https://195.196.36.242/axis-cgi/mediastream.cgi?camera=1&streamprofile=balanced',
    'https://195.196.36.242/axis-cgi/mediastream.cgi?camera=1&streamprofile=low',
]
for ep in endpoints:
    try:
        req = urllib.request.Request(ep, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5, context=ctx) as r:
            data = r.read(2048)
            print(f"  {ep}")
            print(f"    HTTP {r.status} CT={r.headers.get('Content-Type')} first bytes: {data[:100]}")
    except urllib.error.HTTPError as e:
        print(f"  {ep} -> HTTP {e.code}")
    except Exception as e:
        print(f"  {ep} -> err {str(e)[:60]}")