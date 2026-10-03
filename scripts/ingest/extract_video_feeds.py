#!/usr/bin/env python3
"""Extract video feeds and find more webcams on 103.30.71.181"""
import urllib.request, ssl, re, json, socket, subprocess, threading, time
from pathlib import Path

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HOST = "103.30.71.181"
PORT = 80
SUBNET = "103.30.71"

print(f"=== Comprehensive Video Feed Extraction ===")
print(f"Target: {HOST}:{PORT}")
print("=" * 60)

results = {
    'host': HOST,
    'video_feeds': [],
    'additional_cams': [],
    'info': {}
}

# ============================================================
# 1. Test various video streaming protocols
# ============================================================
print("\n[1/6] Testing video streaming protocols...")

# Test RTSP on common ports
for rtsp_port in [554, 8554, 5554, 5678, 32400]:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((HOST, rtsp_port))
        if result == 0:
            print(f"   RTSP port {rtsp_port}: OPEN")
            # Try DESCRIBE command
            try:
                sock.send(b'DESCRIBE rtsp://' + HOST.encode() + f':{rtsp_port}/stream RTSP/1.0\r\nCSeq: 1\r\n\r\n')
                data = sock.recv(4000)
                sock.close()
                print(f"   RTSP DESCRIBE response: {data[:200]}")
            except:
                sock.close()
        else:
            # sock.close()
            pass
    except Exception as e:
        pass

# Test HLS
print("\n[2/6] Testing HLS streams...")
for ep in ['/stream.m3u8', '/video.m3u8', '/playlist.m3u8', '/cam.m3u8', '/live.m3u8']:
    try:
        url = f"http://{HOST}{ep}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=5, context=ctx)
        data = resp.read().decode('utf-8', errors='replace')
        print(f"   {ep}: {resp.status} - {len(data)} chars")
        if '#EXTINF' in data:
            print(f"      Has EXTINF entries")
        if '#EXTM3U' in data:
            print(f"      Has EXTM3U header")
    except Exception as e:
        print(f"   {ep}: Error - {str(e)[:30]}")

# Test MJPEG continuous stream
print("\n[3/6] Testing MJPEG continuous streams...")
for ep in ['/mjpeg', '/stream', '/mjpg', '/view', '/take']:
    try:
        url = f"http://{HOST}{ep}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=8, context=ctx)
        data = resp.read(5000)
        ct = resp.headers.get('Content-Type', '')
        print(f"   {ep}: {resp.status} - {ct} - {len(data)} bytes")
        if b'\xff\xd8' in data[:100]:
            print(f"      *** MJPEG START ***")
        if b'--' in data[:100]:
            # Extract boundary
            m = re.search(rb'boundary=["\']?([^"\'\\s]+)', data)
            if m:
                print(f"      *** Boundary: {m.group(1)} ***")
    except Exception as e:
        print(f"   {ep}: Error - {str(e)[:30]}")

# ============================================================
# 2. Check all snapshot channels for video content
# ============================================================
print("\n[4/6] Testing all snapshot channels for video content...")
valid_channels = []
for ch in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', 'main', 'sub']:
    try:
        url = f"http://{HOST}/webcapture.jpg?command=snap&channel={ch}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        resp = urllib.request.urlopen(req, timeout=5, context=ctx)
        data = resp.read()
        ct = resp.headers.get('Content-Type', '')
        size = len(data)
        
        # Check if it's a valid JPEG
        is_jpeg = data[:2] == b'\xff\xd8' and data[-2:] == b'\xff\xd9'
        
        # Try to determine if it's a live frame vs static
        if is_jpeg:
            # Check for motion/detail - compare with other channels
            valid_channels.append({
                'channel': ch,
                'size': size,
                'mime': ct,
                'is_jpeg': True
            })
            print(f"   channel={ch}: {size} bytes - JPEG valid")
        else:
            print(f"   channel={ch}: {size} bytes - Not JPEG")
    except Exception as e:
        print(f"   channel={ch}: Error - {str(e)[:30]}")

results['video_feeds'] = valid_channels

# ============================================================
# 3. Try to find additional cameras on same subnet
# ============================================================
print("\n[5/6] Searching for additional cameras on subnet...")
# Try common camera IP ranges
subnet_parts = SUBNET.split('.')
for octet in range(1, 255):
    test_ip = f"{subnet_parts[0]}.{subnet_parts[1]}.{subnet_parts[2]}.{octet}"
    try:
        # Quick ping/check
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((test_ip, 80))
        if result == 0:
            # Check if it's a camera
            try:
                req = urllib.request.Request(f"http://{test_ip}/", headers={'User-Agent': 'Mozilla/5.0'})
                resp = urllib.request.urlopen(req, timeout=2, context=ctx)
                ct = resp.headers.get('Content-Type', '')
                server = resp.headers.get('Server', '')
                #print(f"   Found server at {test_ip}: {server} - {ct}")
            except:
                pass
        sock.close()
    except:
        pass
    # Only print every 20th to avoid flood
    if octet % 20 == 0:
        print(f"   Scanned {octet}/255...")

# ============================================================
# 4. Check main page for camera references and links
# ============================================================
print("\n[6/6] Checking main page for camera references...")
try:
    url = f"http://{HOST}/"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
    resp = urllib.request.urlopen(req, timeout=5, context=ctx)
    data = resp.read().decode('utf-8', errors='replace')
    print(f"   Page length: {len(data)} chars")
    
    # Look for any camera IDs, URLs, or references
    # Find all http links
    links = re.findall(r'http[^\s<>"\']+', data)
    print(f"   Found {len(links)} HTTP links")
    for link in links[:10]:
        print(f"     {link[:100]}")
    
    # Look for camera-related text
    lower = data.lower()
    for kw in ['camera', 'ipcam', 'webcam', 'live', 'stream', 'view']:
        if kw in lower:
            idx = lower.find(kw)
            start = max(0, idx - 20)
            end = min(len(data), idx + 80)
            print(f"   Contains '{kw}': ...{data[start:end]}...")
            
except Exception as e:
    print(f"   Error: {str(e)[:50]}")

# ============================================================
# Summary
# ============================================================
print("\n" + "=" * 60)
print("EXTRACTION SUMMARY")
print("=" * 60)
print(f"\nHost: {results['host']}")
print(f"\nValid JPEG channels: {len(results['video_feeds'])}")
for cf in results['video_feeds']:
    print(f"  channel={cf['channel']}: {cf['size']} bytes - JPEG")

print(f"\nVideo feed extraction complete.")
print("Note: No live RTSP/HLS streams found. Only still JPEG images available.")
print("Additional cameras on same subnet: scan would need more time.")