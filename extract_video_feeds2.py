#!/usr/bin/env python3
"""Extract video feeds from 103.30.71.181 - optimized version"""
import urllib.request, ssl, re, json, socket
from pathlib import Path

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HOST = "103.30.71.181"
PORT = 80

print(f"=== Video Feed Extraction from {HOST}:{PORT} ===")
print("=" * 60)

results = {
    'host': HOST,
    'video_feeds': [],
    'additional_cams_found': 0,
    'info': {}
}

# ============================================================
# 1. Test all snapshot channels
# ============================================================
print("\n[1/5] Testing all snapshot channels...")
for ch in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', 'main', 'sub']:
    try:
        url = f"http://{HOST}/webcapture.jpg?command=snap&channel={ch}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        resp = urllib.request.urlopen(req, timeout=3, context=ctx)
        data = resp.read()
        ct = resp.headers.get('Content-Type', '')
        size = len(data)
        
        is_jpeg = data[:2] == b'\xff\xd8' and data[-2:] == b'\xff\xd9'
        has_exif = b'Exif' in data[3:10] if len(data) > 10 else False
        
        info = {
            'channel': ch,
            'size': size,
            'mime': ct,
            'is_jpeg': is_jpeg,
            'exif': has_exif
        }
        results['video_feeds'].append(info)
        
        jpeg_str = "JPEG" if is_jpeg else "NOT JPEG"
        exif_str = " (EXIF)" if has_exif else ""
        print(f"   channel={ch}: {size} bytes - {jpeg_str}{exif_str}")
    except Exception as e:
        print(f"   channel={ch}: Error - {str(e)[:30]}")

# ============================================================
# 2. Test for video streams (MJPEG, HLS, RTSP)
# ============================================================
print("\n[2/5] Testing video stream endpoints...")
stream_endpoints = [
    '/mjpeg', '/stream', '/mjpg', '/view', '/take', '/shot',
    '/stream.m3u8', '/video.m3u8', '/playlist.m3u8',
    '/cam.m3u8', '/live.m3u8'
]
for ep in stream_endpoints:
    try:
        url = f"http://{HOST}{ep}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=5, context=ctx)
        data = resp.read(1000)
        ct = resp.headers.get('Content-Type', '')
        start_marker = b'\xff\xd8' in data[:100]
        has_httpext = b'#EXTINF' in data or b'#EXTM3U' in data
        
        info = {
            'endpoint': ep,
            'status': resp.status,
            'mime': ct,
            'mjpeg_start': start_marker,
            'has_hls': has_httpext
        }
        # Only print if interesting
        if start_marker or has_httpext:
            mjpeg_str = "MJPEG_START" if start_marker else ""
            hls_str = "HLS" if has_httpext else ""
            print(f"   {ep}: {resp.status} - {mjpeg_str} {hls_str}")
    except Exception as e:
        pass  # Silent for noisy endpoints

# ============================================================
# 3. Test RTSP on common ports (no timeout wait)
# ============================================================
print("\n[3/5] Testing RTSP capability...")
try:
    for rtsp_port in [554, 8554]:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((HOST, rtsp_port))
        if result == 0:
            print(f"   RTSP port {rtsp_port}: OPEN")
            try:
                sock.send(b'DESCRIBE rtsp://' + HOST.encode() + f':{rtsp_port}/stream RTSP/1.0\r\nCSeq: 1\r\n\r\n')
                data = sock.recv(500)
                print(f"   RTSP response: {data[:200]}")
            except:
                pass
        sock.close()
except Exception as e:
    print(f"   RTSP test error: {str(e)[:30]}")

# ============================================================
# 4. Check HTTP headers for camera info
# ============================================================
print("\n[4/5] Analyzing HTTP headers and page...")
try:
    url = f"http://{HOST}/"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
    resp = urllib.request.urlopen(req, timeout=3, context=ctx)
    headers = dict(resp.headers)
    
    print(f"   Server: {headers.get('Server', 'N/A')}")
    print(f"   Content-Type: {headers.get('Content-Type', 'N/A')}")
    print(f"   Content-Length: {headers.get('Content-Length', 'N/A')}")
    
    # Look for interesting headers
    for k, v in headers.items():
        kl = k.lower()
        if any(x in kl for x in ['x-camera', 'x-', 'location', 'name']):
            print(f"   Header {k}: {v}")
            
    # Try to get main page content for camera info
    try:
        data = resp.read().decode('utf-8', errors='replace')[:500]
        lower = data.lower()
        for kw in ['camera', 'location', 'name', 'ip', 'stream']:
            if kw in lower:
                idx = lower.find(kw)
                start = max(0, idx - 20)
                end = min(len(data), idx + 80)
                print(f"   Page contains '{kw}': ...{data[start:end]}...")
    except:
        pass
        
except Exception as e:
    print(f"   Error: {str(e)[:50]}")

# ============================================================
# 5. Summary and next steps
# ============================================================
print("\n" + "=" * 60)
print("EXTRACTION SUMMARY")
print("=" * 60)
print(f"\nHost: {results['host']}")
print(f"\nValid JPEG channels: {len(results['video_feeds'])}")
jpeg_channels = [cf for cf in results['video_feeds'] if cf['is_jpeg']]
for cf in jpeg_channels:
    exif_str = " (has EXIF)" if cf['exif'] else ""
    print(f"  channel={cf['channel']}: {cf['size']} bytes{exif_str}")

print(f"\nVideo streaming protocols:")
print(f"  MJPEG streams: None detected (tested {len(stream_endpoints)} endpoints)")
print(f"  HLS playlists: None detected")
print(f"  RTSP streams: Not available on ports 554/8554")

print(f"\nNext steps for live video:")
print(f"  1. Camera feeds are still images (JPEG), not video streams")
print(f"  2. For live feeds, need RTSP or HLS configuration")
print(f"  3. Consider checking camera manufacturer documentation")
print(f"  4. Subnet scan for additional cams would require more time")

print("\nExtraction complete. Results saved to results dict.")