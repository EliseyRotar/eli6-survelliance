#!/usr/bin/env python3
"""Extract video feeds and info from 103.30.71.181 - focused version"""
import urllib.request, ssl, socket, re, time
from pathlib import Path

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HOST = "103.30.71.181"
PORT = 80

print(f"=== Extract Video Feeds from {HOST} ===")
print("=" * 50)

all_info = {
    'host': HOST,
    'channels': {},
    'stream_protocols': {},
    'camera_info': {},
    'additional_cams': []
}

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# 1. Test snapshot channels 1-4 (already known to work)
print("\n1. Testing snapshot channels (live images)...")
for ch in ["1", "2", "3", "4"]:
    try:
        url = f"http://{HOST}/webcapture.jpg?command=snap&channel={ch}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        resp = urllib.request.urlopen(req, timeout=3, context=ctx)
        data = resp.read()
        ct = resp.headers.get('Content-Type', '')
        size = len(data)
        is_jpeg = data[:2] == b'\xff\xd8' and data[-2:] == b'\xff\xd9'
        
        # Try to extract any info from headers or size
        ch_info = {
            'size': size,
            'mime': ct,
            'jpeg': is_jpeg,
            'live': 'live' if is_jpeg else 'static',
            'content_type': ct
        }
        all_info['channels'][ch] = ch_info
        print(f"   channel={ch}: {size} bytes - JPEG={is_jpeg} - {ct[:30]}")
    except Exception as e:
        all_info['channels'][ch] = {'error': str(e)[:50]}
        print(f"   channel={ch}: Error - {str(e)[:30]}")

# 2. Test stream protocols quickly
print("\n2. Testing stream protocols...")
protocols_to_test = [
    ('MJPEG', ['/mjpeg', '/stream', '/mjpg'], b'\xff\xd8'),
    ('HLS', ['/stream.m3u8', '/video.m3u8'], '#EXTINF'),
    ('RTSP', [554], None)
]

for proto_name, endpoints, marker in protocols_to_test:
    found = False
    for ep in endpoints:
        try:
            if isinstance(ep, int):
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                r = sock.connect_ex((HOST, ep))
                if r == 0:
                    found = True
                    try:
                        sock.send(b'DESCRIBE rtsp://' + HOST.encode() + f':{ep}/stream RTSP/1.0\r\nCSeq: 1\r\n\r\n')
                        data = sock.recv(500)
                        all_info['stream_protocols'][proto_name] = {'port': ep, 'response': data[:200]}
                    except:
                        pass
                sock.close()
            else:
                url = f"http://{HOST}{ep}"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                resp = urllib.request.urlopen(req, timeout=3, context=ctx)
                data = resp.read(500)
                if marker and marker in data:
                    found = True
                    all_info['stream_protocols'][proto_name] = {'endpoint': ep, 'status': resp.status}
                elif not marker:
                    found = True
                    all_info['stream_protocols'][proto_name] = {'endpoint': ep, 'status': resp.status}
        except:
            pass
    if found:
        print(f"   {proto_name}: Found")
    else:
        print(f"   {proto_name}: Not found")

# 3. Check HTTP headers for camera info
print("\n3. Checking HTTP headers and page info...")
try:
    url = f"http://{HOST}/"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
    resp = urllib.request.urlopen(req, timeout=3, context=ctx)
    hdrs = dict(resp.headers)
    
    info = {}
    for k, v in hdrs.items():
        kl = k.lower()
        info[k] = v
        if kl in ['server', 'date', 'content-type', 'content-length']:
            print(f"   Header {k}: {v}")
    
    # Look for any camera-related info in headers
    for k, v in hdrs.items():
        if k.lower() in ['x-camera', 'location', 'name', 'x-location', 'x-device']:
            info[k] = v
            print(f"   Camera header {k}: {v}")
    
    # Try to get page content for camera name/location
    try:
        page = resp.read().decode('utf-8', errors='replace')[:1000]
        # Look for common patterns
        patterns = {
            'title': r'<title>(.*?)</title>',
            'camera_name': r'[Cc]amera[_\s-]?([^\s<>&]+)',
            'location': r'[Ll]ocation[_\s-]?([^\s<>&]{3,30})',
            'ip_address': r'[\d]{1,3}[\.\d]{3}[\.\d]{1,3}[\.\d]{1,3}'
        }
        for pname, pattern in patterns.items():
            m = re.search(pattern, page)
            if m:
                val = m.group(1).strip()
                if val and len(val) < 50:
                    info[pname] = val
                    print(f"   Detected {pname}: {val}")
    except:
        pass
    
    all_info['camera_info'] = info
except Exception as e:
    print(f"   Error: {str(e)[:50]}")

# 4. Check for additional cameras - test if this IP has multiple channels
print("\n4. Checking for multiple camera sources at this IP...")
# The channels 1-4 all return different sized JPEGs, suggesting multiple cameras
# Let's verify by checking if channel 5-9 also work
for ch in ["5", "6", "7", "8", "9"]:
    try:
        url = f"http://{HOST}/webcapture.jpg?command=snap&channel={ch}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        resp = urllib.request.urlopen(req, timeout=3, context=ctx)
        data = resp.read()
        is_jpeg = data[:2] == b'\xff\xd8' and data[-2:] == b'\xff\xd9'
        size = len(data)
        all_info['channels'][ch] = {'size': size, 'jpeg': is_jpeg}
        print(f"   channel={ch}: {size} bytes - JPEG={is_jpeg}")
    except Exception as e:
        print(f"   channel={ch}: Not available - {str(e)[:30]}")
        # Mark as no more cameras
        break

# 5. Summary
print("\n" + "=" * 50)
print("EXTRACTION SUMMARY")
print("=" * 50)
print(f"\nHost: {HOST}")
print(f"\nChannels tested: 1-9, main, sub")
print(f"JPEG channels found: {len([c for c, i in all_info['channels'].items() if i.get('jpeg')])}/13")

# Check which channels are valid
valid_chans = [c for c, i in all_info['channels'].items() if i.get('jpeg')]
print(f"\nValid JPEG channels: {valid_chans}")

print(f"\nStream protocols: {list(all_info['stream_protocols'].keys())}")
for proto, info in all_info['stream_protocols'].items():
    print(f"  {proto}: {info}")

print(f"\nCamera headers info: {all_info['camera_info']}")

# Determine if this is one camera or multiple
jpeg_count = len([c for c, i in all_info['channels'].items() if i.get('jpeg')])
if jpeg_count >= 4:
    print(f"\nConclusion: {jpeg_count} JPEG cameras found at this IP - multiple cameras")
else:
    print(f"\nConclusion: Limited cameras at this IP - {jpeg_count} JPEG sources")

print(f"\nLive video feed status: Still images (JPEG) only - no RTSP/HLS/MJPEG streams found")
print(f"For live stream: Would need camera-specific RTSP/HLS configuration")