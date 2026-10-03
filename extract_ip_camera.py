#!/usr/bin/env python3
"""
Comprehensive IP Camera Extraction Tool
Extracts video feeds, location, name, and all possible info from 103.30.71.181
"""
import urllib.request, ssl, re, json, socket, time
from pathlib import Path

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HOST = "103.30.71.181"
PORT = 80
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

print(f"=== IP Camera Extraction Tool ===")
print(f"Target: {HOST}:{PORT}")
print("=" * 60)

results = {
    'host': HOST,
    'channels': [],
    'streams': [],
    'info': {}
}

# ============================================================
# 1. Test all snapshot channels (1-9, main, sub)
# ============================================================
print("\n[1/7] Testing snapshot channels...")
for ch in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', 'main', 'sub']:
    channel_info = {
        'channel': ch,
        'snapshot_url': f"http://{HOST}/webcapture.jpg?command=snap&channel={ch}",
        'status': None,
        'size': 0,
        'content_type': '',
        'mime_type': '',
        'jpeg_valid': False,
        'exif': False,
        'size_bytes': 0
    }
    try:
        url = channel_info['snapshot_url']
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        resp = urllib.request.urlopen(req, timeout=5, context=ctx)
        data = resp.read()
        ct = resp.headers.get('Content-Type', '')
        size = len(data)
        
        channel_info['status'] = resp.status
        channel_info['content_type'] = ct
        channel_info['size_bytes'] = size
        
        # Check JPEG validity
        if data[:2] == b'\xff\xd8':
            channel_info['jpeg_valid'] = True
            channel_info['mime_type'] = 'image/jpeg'
        
        # Check for EXIF
        if data.find(b'Exif\\x00\\x00') > 0 or (data[2:3] == b'\\xe1' and len(data) > 5 and data[5:9] == b'Exif\\x00\\x00'):
            channel_info['exif'] = True
        
        # Check for JFIF
        if data[2:3] == b'\\xe0' and len(data) > 5:
            channel_info['jfif'] = True
        
        print(f"   channel={ch}: {resp.status} - {ct} - {size} bytes - JPEG: {channel_info['jpeg_valid']} - EXIF: {channel_info['exif']}")
        
    except Exception as e:
        print(f"   channel={ch}: Error - {str(e)[:50]}")
    
    results['channels'].append(channel_info)

# ============================================================
# 2. Test MJPEG streams
# ============================================================
print("\n[2/7] Testing MJPEG streams...")
for ep in ['/mjpeg', '/stream', '/mjpeg/stream', '/view', '/take', '/shot', '/mjpg']:
    stream_info = {
        'endpoint': ep,
        'status': None,
        'content_type': '',
        'mime_type': '',
        'boundary': None,
        'mjpeg_start': False
    }
    try:
        url = f"http://{HOST}{ep}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        resp = urllib.request.urlopen(req, timeout=8, context=ctx)
        data = resp.read(2000)
        ct = resp.headers.get('Content-Type', '')
        
        stream_info['status'] = resp.status
        stream_info['content_type'] = ct
        
        # Check for MJPEG start
        if b'\\xff\\xd8' in data[:100]:
            stream_info['mjpeg_start'] = True
        
        # Extract boundary
        m = re.search(rb'boundary=["\']?([^"\'\\s]+)', data)
        if m:
            stream_info['boundary'] = m.group(1).decode('utf-8', errors='replace')
        
        # Check for -- multipart
        if b'--' in data[:50]:
            stream_info['multipart'] = True
        
        print(f"   {ep}: {resp.status} - {ct} - MJPEG start: {stream_info['mjpeg_start']} - Boundary: {stream_info.get('boundary', 'N/A')}")
        
    except Exception as e:
        print(f"   {ep}: Error - {str(e)[:50]}")
    
    results['streams'].append(stream_info)

# ============================================================
# 3. Test CGI endpoints for camera info
# ============================================================
print("\n[3/7] Testing CGI endpoints...")
cgi_endpoints = [
    '/cgi-bin/getdevinfo',
    '/cgi-bin/getsysteminfo', 
    '/cgi-bin/getstatus',
    '/cgi-bin/getconfig',
    '/cgi-bin/status',
    '/api/getinfo',
    '/json',
    '/camera'
]

for ep in cgi_endpoints:
    try:
        url = f"http://{HOST}{ep}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        resp = urllib.request.urlopen(req, timeout=5, context=ctx)
        data = resp.read().decode('utf-8', errors='replace')
        ct = resp.headers.get('Content-Type', '')
        
        # Extract key info
        info = {}
        for kw in ['model', 'serial', 'firmware', 'version', 'name', 'location']:
            m = re.search(rf'{kw}[\"\\'=:\\s]+([^\"\\'\\s:]+)', data, re.IGNORECASE)
            if m:
                info[kw] = m.group(1).strip()
        
        if info:
            print(f"   {ep}: Found info - {info}")
            results['info'].setdefault(ep, info)
        else:
            print(f"   {ep}: No key info found (status: {resp.status}, ct: {ct})")
            
    except Exception as e:
        print(f"   {ep}: Error - {str(e)[:50]}")

# ============================================================
# 4. Test HTTP headers and basic info
# ============================================================
print("\n[4/7] Testing HTTP headers and basic info...")
try:
    url = f"http://{HOST}/"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
    resp = urllib.request.urlopen(req, timeout=5, context=ctx)
    
    headers = dict(resp.headers)
    print(f"   Server header: {headers.get('Server', 'N/A')}")
    print(f"   Date: {headers.get('Date', 'N/A')}")
    print(f"   Content-Type: {headers.get('Content-Type', 'N/A')}")
    print(f"   Content-Length: {headers.get('Content-Length', 'N/A')}")
    
    # Look for any interesting headers
    for k, v in headers.items():
        kl = k.lower()
        if any(x in kl for x in ['x-camera', 'x-', 'server', 'public', 'www-auth']):
            print(f"   Header {k}: {v}")
            
except Exception as e:
    print(f"   Error: {str(e)[:50]}")

# ============================================================
# 5. Test for RTSP stream
# ============================================================
print("\n[5/7] Testing RTSP endpoint...")
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect((HOST, 554))
    sock.send(b'DESCRIBE rtsp://{HOST}/stream RTSP/1.0\r\nCSeq: 1\r\nAccept: application/sdp\r\n\r\n')
    data = sock.recv(4000)
    sock.close()
    print(f"   RTSP response: {data[:300]}")
except Exception as e:
    print(f"   RTSP Error: {str(e)[:50]}")

# ============================================================
# 6. Test HLS playlist
# ============================================================
print("\n[6/7] Testing HLS playlist...")
for ep in ['/stream.m3u8', '/video.m3u8', '/playlist.m3u8', '/cam.m3u8']:
    try:
        url = f"http://{HOST}{ep}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        resp = urllib.request.urlopen(req, timeout=5, context=ctx)
        data = resp.read().decode('utf-8', errors='replace')
        print(f"   {ep}: {resp.status} - {len(data)} chars")
        # Look for any stream info
        if '#EXTINF' in data:
            print(f"      Has EXTINF entries")
        if '#EXTM3U' in data:
            print(f"      Has EXTM3U header")
        # Look for URLs
        urls = re.findall(r'https?://[^\s"\'<>]+', data)
        if urls:
            print(f"      URLs: {urls[:3]}")
    except Exception as e:
        print(f"   {ep}: Error - {str(e)[:30]}")

# ============================================================
# 7. Check main page for camera references
# ============================================================
print("\n[7/7] Checking main page...")
try:
    url = f"http://{HOST}/"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
    resp = urllib.request.urlopen(req, timeout=5, context=ctx)
    data = resp.read().decode('utf-8', errors='replace')
    print(f"   Page title/length: {len(data)} chars")
    
    # Look for camera-related content
    lower = data.lower()
    for kw in ['camera', 'ipcam', 'webcam', 'surveillance', 'live', 'stream']:
        if kw in lower:
            idx = lower.find(kw)
            # Get surrounding context
            start = max(0, idx - 30)
            end = min(len(data), idx + 100)
            print(f"   Contains '{kw}': ...{data[start:end]}...")
    
    # Look for any JSON-LD or structured data
    json_ld = re.search(r'<script type="application/ld\+json">(.*?)</script>', data, re.DOTALL)
    if json_ld:
        print(f"   JSON-LD found: {json_ld.group(1)[:200]}")
        
except Exception as e:
    print(f"   Error: {str(e)[:50]}")

# ============================================================
# Summary
# ============================================================
print("\n" + "=" * 60)
print("EXTRACTION SUMMARY")
print("=" * 60)

# Count valid channels
valid_channels = [c for c in results['channels'] if c['jpeg_valid']]
print(f"\nValid JPEG channels: {len(valid_channels)}/9 tested")
for c in valid_channels:
    exif_str = " (EXIF)" if c['exif'] else ""
    jfif_str = " (JFIF)" if c.get('jfif') else ""
    print(f"  channel={c['channel']}: {c['size_bytes']} bytes{exif_str}{jfif_str}")

# Count streams with MJPEG
mjpeg_streams = [s for s in results['streams'] if s.get('mjpeg_start')]
print(f"\nMJPEG streams detected: {len(mjpeg_streams)}/{len(results['streams'])}")

# Summary info
if results['info']:
    print(f"\nCGI endpoints with info: {len(results['info'])}")
    for ep, info in results['info'].items():
        print(f"  {ep}: {info}")

# Check if we can determine location/name
print(f"\nHost: {results['host']}")
print("Extraction complete. Results saved to results dict.")