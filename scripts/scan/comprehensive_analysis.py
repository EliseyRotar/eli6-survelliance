import urllib.request, ssl, socket, re, json
from pathlib import Path

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
HOST = "103.30.71.181"

print("=== Comprehensive Camera Analysis ===")
print("=" * 50)

# 1. Test all snapshot channels
print("\n1. Snapshot channels (already tested: ch1-4 JPEG)")
for ch in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "main", "sub"]:
    try:
        url = f"http://{HOST}/webcapture.jpg?command=snap&channel={ch}"
        resp = urllib.request.urlopen(url, timeout=3, context=ctx)
        data = resp.read()
        is_jpeg = data[:2] == b'\xff\xd8' and data[-2:] == b'\xff\xd9'
        ct = resp.headers.get('Content-Type', '')
        print(f"   channel={ch}: {len(data)} bytes JPEG={is_jpeg}")
    except Exception as e:
        print(f"   channel={ch}: Error - {str(e)[:30]}")

# 2. Test streaming endpoints quickly
print("\n2. Streaming endpoints (quick test)...")
for ep in ["/mjpeg", "/stream", "/mjpg"]:
    try:
        url = f"http://{HOST}{ep}"
        resp = urllib.request.urlopen(url, timeout=3, context=ctx)
        data = resp.read(500)
        has_jpeg_start = b'\xff\xd8' in data[:100]
        print(f"   {ep}: {resp.status} bytes={len(data)} MJPEG_start={has_jpeg_start}")
    except Exception as e:
        print(f"   {ep}: Error - {str(e)[:30]}")

# 3. Test RTSP quick
print("\n3. RTSP test...")
for port in [554]:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        r = sock.connect_ex((HOST, port))
        if r == 0:
            print(f"   RTSP port {port}: OPEN")
            sock.send(b'DESCRIBE rtsp://' + HOST.encode() + f':{port}/stream RTSP/1.0\r\nCSeq: 1\r\n\r\n')
            data = sock.recv(500)
            print(f"   Response: {data[:100]}")
        sock.close()
    except Exception as e:
        print(f"   RTSP port {port}: Error - {str(e)[:30]}")

# 4. HLS quick test
print("\n4. HLS test...")
for ep in ["/stream.m3u8", "/video.m3u8"]:
    try:
        url = f"http://{HOST}{ep}"
        resp = urllib.request.urlopen(url, timeout=3, context=ctx)
        data = resp.read(200).decode('utf-8', errors='replace')
        has_extinf = '#EXTINF' in data
        has_extm3u = '#EXTM3U' in data
        print(f"   {ep}: {resp.status} EXTINF={has_extinf} EXTM3U={has_extm3u}")
    except Exception as e:
        print(f"   {ep}: Error - {str(e)[:30]}")

# 5. Check HTTP headers
print("\n5. HTTP headers...")
try:
    url = f"http://{HOST}/"
    resp = urllib.request.urlopen(url, timeout=3, context=ctx)
    hdrs = dict(resp.headers)
    print(f"   Server: {hdrs.get('Server', 'N/A')}")
    print(f"   Date: {hdrs.get('Date', 'N/A')}")
    for k, v in hdrs.items():
        if k.lower() in ['x-camera', 'location', 'name']:
            print(f"   Header {k}: {v}")
except Exception as e:
    print(f"   Error: {str(e)[:30]}")

# 6. Try to find more cameras by varying the channel
print("\n5. Testing additional channels 5-9...")
for ch in ["5", "6", "7", "8", "9"]:
    try:
        url = f"http://{HOST}/webcapture.jpg?command=snap&channel={ch}"
        resp = urllib.request.urlopen(url, timeout=3, context=ctx)
        data = resp.read()
        is_jpeg = data[:2] == b'\xff\xd8' and data[-2:] == b'\xff\xd9'
        ct = resp.headers.get('Content-Type', '')
        print(f"   channel={ch}: {len(data)} bytes JPEG={is_jpeg} - {ct[:30]}")
    except Exception as e:
        print(f"   channel={ch}: Error - {str(e)[:30]}")

print("\n=== Analysis Complete ===")