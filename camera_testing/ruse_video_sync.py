"""Ruse VIDEO finder - SYNC version with print().

Tests video URL patterns for each Ruse cam.
"""

import os
import re
import socket
import time
import urllib.request
import urllib.error
import ssl

OUT_DIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance\recon\dossier_ruse\video_streams"
os.makedirs(OUT_DIR, exist_ok=True)

URLS_TO_CHECK = [
    "http://info.weather.yandex.net/20758/3.png",  # Yandex - has video!
    "https://images-webcams.windy.com/15/1597690315/current/full/1597690315.jpg",
    "https://images-webcams.windy.com/15/1793898215/current/full/1793898215.jpg",
    "https://images-webcams.windy.com/97/1793902097/current/full/1793902097.jpg",
    "https://www.img.worldcam.pl/webcams/200x113/2026-08-25/14906.jpg",
    "https://www.img.worldcam.pl/webcams/200x113/2026-08-25/24496.jpg",
    "https://www.img.worldcam.pl/webcams/200x113/2026-08-25/2706.jpg",
    "https://www.img.worldcam.pl/webcams/200x113/2026-08-25/37360.jpg",
    "https://www.img.worldcam.pl/webcams/200x113/2026-08-25/40580.jpg",
]


def probe_rtsp(host, port, path, timeout=6):
    """Try RTSP DESCRIBE."""
    try:
        url = f'rtsp://{host}:{port}{path}'
        sock = socket.create_connection((host, port), timeout=timeout)
        req = f'DESCRIBE {url} RTSP/1.0\r\nCSeq: 1\r\nUser-Agent: Mozilla/5.0\r\n\r\n'
        sock.send(req.encode())
        data = b''
        sock.settimeout(timeout)
        try:
            while b'\r\n\r\n' not in data and len(data) < 4096:
                d = sock.recv(1024)
                if not d:
                    break
                data += d
        except socket.timeout:
            pass
        sock.close()
        if b'200 OK' in data[:200]:
            m = re.search(rb'Content-Type:\s*([^\r\n]+)', data, re.I)
            ct = m.group(1).decode() if m else 'application/sdp'
            return ('RTSP', 200, ct)
        elif b'401' in data[:500]:
            return ('RTSP', 401, 'auth')
        elif b'404' in data[:200] or b'Not Found' in data[:200]:
            return ('RTSP', 404, 'not_found')
        return ('RTSP', None, f'no_resp:{data[:100]}')
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        return ('RTSP', None, f'unreachable')
    except Exception as e:
        return ('RTSP', None, f'err:{str(e)[:30]}')


def probe_http(url, timeout=5):
    """Try HTTP/HTTPS URL."""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': '*/*'})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            data = r.read()
            ct = r.headers.get('Content-Type', '')
            return ('HTTP', r.status, ct, len(data))
    except urllib.error.HTTPError as e:
        return ('HTTP', e.code, '', 0)
    except Exception as e:
        return ('HTTP', None, str(e)[:50], 0)


print('=== Yandex Test - Dedicated Video Formats ===')
# Yandex weather cams use info.weather.yandex.net/<cam_id>/<size>.png for images
# Check if they have video format
for cam_id in [20758]:
    for n in [1, 2, 3, 4]:
        for ext in ['png', 'jpg', 'webp', 'mp4', 'webm', 'm3u8']:
            url = f'http://info.weather.yandex.net/{cam_id}/{n}.{ext}'
            res = probe_http(url, timeout=4)
            print(f'  Yandex {cam_id}/{n}.{ext}: {res}')
    # Try special yandex paths
    for path in [
        f'/video/{cam_id}',
        f'/xchk/{cam_id}',
        f'/xchk/{cam_id}.mp4',
        f'/static/video/{cam_id}.mp4',
        f'/video/{cam_id}.webm',
    ]:
        url = f'http://info.weather.yandex.net{path}'
        res = probe_http(url, timeout=4)
        print(f'  Yandex {path}: {res}')


print('\n=== Worldcam Test - Direct MP4/WebM formats ===')
for cam_id in [14906, 24496, 2706, 37360, 40580]:
    # Worldcam has m3u8 streams
    for sz in ['400x226', 'original']:
        for ext in ['mp4', 'webm', 'm3u8']:
            url = f'https://www.img.worldcam.pl/webcams/{sz}/2026-08-25/{cam_id}.{ext}'
            res = probe_http(url, timeout=4)
            print(f'  WC/{cam_id}.{ext}: {res}')


print('\n=== Windy Test - Other Paths ===')
for wid in [1597690315, 1793898215, 1793902097]:
    # Windy stores individual snaps but might have video
    paths = [
        f'/15/{wid}/current/full/{wid}.jpg',
        f'/15/{wid}/daylight/full/{wid}.jpg',
        f'/15/{wid}/current/full/{wid}.mp4',
        f'/15/{wid}/current/full/{wid}.webm',
        f'/15/{wid}/video.mp4',
        f'/97/{wid}/current/full/{wid}.mp4',
    ]
    for path in paths:
        url = f'https://images-webcams.windy.com{path}'
        res = probe_http(url, timeout=5)
        print(f'  Windy{wid} {path[-50:]}: {res}')


print('\n=== Ruse-specific InternetDB cam video checks ===')
# Test discovered Ruse IPs with video paths
for ip in ['2.56.54.0', '5.32.134.0', '31.13.192.128']:
    for path in ['/', '/mjpg/video.mjpg', '/axis-cgi/mjpg/video.cgi']:
        url = f'http://{ip}{path}'
        res = probe_http(url, timeout=4)
        if res[1] in [200, 404]:
            print(f'  {ip}{path}: {res}')


print('\n=== Search for live Ruse aggregator video pages ===')
# Skyline, Webcams.travel, Earthcam search
for url in [
    'https://www.worldcam.eu/api/webcams/ruse/list',
    'https://en.webcams.travel/webcam/Ruse-Bulgaria',
]:
    res = probe_http(url, timeout=10)
    print(f'  {url}: {res}')


print('\nDone.')
