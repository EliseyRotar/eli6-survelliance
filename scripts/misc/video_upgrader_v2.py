"""Smart video discovery - find ACTUAL IP CAMS with video streams.

Strategy:
1. Filter image URLs to only those on IPs (not aggregator CDN hosts)
2. Probe with VIDEO patterns
3. Update to video-mjpeg or video-h264

Cams to focus on:
- URLs with IPs (e.g. http://1.2.3.4:8080/...)
- NOT aggregator domains (worldcam.pl, windy.com, etc.)
"""
import os
import csv
import re
import time
import json
import socket
import random
import ssl
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed

WORKDIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance"

# Find CSV
import glob
CSV_PATH = None
for f in glob.glob(r'C:\Users\eli6-admin\Documents\**/controllable_Webcams.csv', recursive=True):
    CSV_PATH = f
    break

if not CSV_PATH:
    print('CSV not found')
    exit(1)
print(f'CSV: {CSV_PATH}')

PROGRESS_PATH = os.path.join(os.path.dirname(CSV_PATH), "camera_testing", "video_upgrade_v2_progress.json")

# Common video paths to try
VIDEO_PATHS = [
    # AXIS (most common in IP cam aggregators)
    ('/axis-cgi/mjpg/video.cgi', 'AXIS', 'multipart'),
    # Hikvision
    ('/Streaming/tracks/101', 'Hikvision', 'video'),
    # Dahua
    ('/cam/realmonitor?channel=1&subtype=0', 'Dahua', 'multipart'),
    # Generic MJPEG
    ('/mjpg/video.mjpg', 'Generic', 'multipart'),
    # Canon VB
    ('/-wvhttp-01-/getoneshot?image=img', 'Canon', 'jpeg'),
    # WebcamXP
    ('/cam_1.cgi', 'WebcamXP', 'multipart'),
    # Blue Iris
    ('/image', 'BlueIris', 'jpeg'),
    # Other common
    ('/video.cgi', 'Generic', 'video'),
    ('/stream.cgi', 'Generic', 'video'),
    ('/videostream.cgi', 'Generic', 'video'),
]

# Aggregator domains to SKIP (no video behind image proxy)
SKIP_DOMAINS = [
    'windy.com', 'worldcam.pl', 'img.worldcam.pl', 'worldcam.eu', 'webcams.windy.com',
    'images-webcams.windy.com', 'yandex.net', 'easeweather.com', 'weather-webcam.eu',
    'res.easeweather.com', 'webcamsbg.com', 'webcamera24.com', 'webcamgalore.com',
    'webcams.travel', 'city-webcams.com', 'earthcam.com', 'skylinewebcams.com',
    'spotcameras.com', 'opentopia.com', 'rtsp.me', 'abc.xyz', 'google.com', 'googletagmanager.com',
    'gstatic.com', 'facebook.com', 'twitter.com', 'instagram.com', 'youtube.com', 'ytimg.com',
    'paypal.com', 'gomex.com', 'facebook.com',
]


def is_ip_or_rare_domain(url):
    """Check if URL is on an IP or non-aggregator domain."""
    m = re.match(r'https?://([^/]+)', url)
    if not m:
        return False
    host = m.group(1)
    # Strip port
    host_only = host.split(':')[0]
    # Is it an IP?
    try:
        ipaddress.ip_address(host_only)
        return True
    except:
        pass
    # Is it a non-aggregator domain?
    for skip in SKIP_DOMAINS:
        if skip in host:
            return False
    # Check if it's a known cam domain
    if any(d in host for d in ['cam', 'cctv', 'camera', 'webcam', 'dvr', 'nvr', 'axis-cgi', 'streaming', 'live', 'view', 'monitor']):
        return True
    # Check if it's a generic IP cam (no aggregator patterns)
    return True


def probe_video(host, port, path, timeout=3):
    """Try video URL. Returns (status, content_type, is_video) or None."""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        req = f'GET {path} HTTP/1.0\r\nHost: {host}\r\nUser-Agent: Mozilla/5.0\r\nConnection: close\r\n\r\n'
        sock.send(req.encode())
        data = b''
        sock.settimeout(timeout)
        try:
            while len(data) < 8000:
                d = sock.recv(4096)
                if not d: break
                data += d
        except: pass
        sock.close()
        if b'200 OK' in data[:300]:
            ct = ''
            for line in data.split(b'\r\n')[:20]:
                if line.lower().startswith(b'content-type:'):
                    ct = line[12:].strip().decode('utf-8', errors='replace').lower()
                    break
            # MJPEG multipart, or video container
            is_video = any(s in ct for s in [
                'multipart/x-mixed-replace', 'video/', 'hls', 'mpeg', 'mp4', 'octet-stream',
                'image/jpeg', 'image/jpg', 'image/png'
            ])
            # Verify body is binary
            _, _, body = data.partition(b'\r\n\r\n')
            is_jpeg = body.startswith(b'\xff\xd8')
            is_png = body.startswith(b'\x89PNG')
            is_xml = body.startswith(b'<?xml') or body.startswith(b'<')
            if is_jpeg and 'image/jpeg' in ct:
                is_video = True
            if is_png and 'image/png' in ct:
                is_video = True
            return (200, ct, is_video)
        elif b'401' in data[:500]:
            return (401, '', False)
    except Exception:
        return None
    return None


def main():
    print(f'[Video V2] Smart discovery on cam IPs/domains (not aggregators)')

    csv.field_size_limit(2**31 - 1)
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    # Filter to image URLs on IPs or non-aggregator domains
    targets = []
    for i, r in enumerate(rows):
        if (r.get('type') or '') != 'image':
            continue
        url = r.get('url', '') or r.get('live_stream_url', '')
        if not url:
            continue
        if not is_ip_or_rare_domain(url):
            continue
        m = re.match(r'https?://([^/]+)(/.*)?', url)
        if not m:
            continue
        host_port = m.group(1)
        if ':' in host_port:
            host, port = host_port.rsplit(':', 1)
            try:
                port = int(port)
            except:
                port = 80
        else:
            host = host_port
            port = 80
        targets.append((i, host, port, r))

    print(f'  {len(targets)} image cams to probe (excluding aggregators)')

    progress = {}
    if os.path.exists(PROGRESS_PATH):
        try:
            with open(PROGRESS_PATH) as f:
                progress = json.load(f)
        except:
            progress = {'tested': {}, 'upgraded': 0, 'videos': []}
    tested = progress.get('tested', {})

    upgraded = 0
    upgraded_rows = []
    found_videos = []

    def probe_target(args):
        i, host, port, row = args
        key = f'{host}:{port}'
        if key in tested and tested[key].get('video'):
            return None

        best = None
        for path, vendor, kind in VIDEO_PATHS:
            r = probe_video(host, port, path, timeout=2)
            if r and r[0] == 200 and r[2]:
                # Prefer multipart (live video) over jpeg
                if not best:
                    best = (path, vendor, r[1])
                elif 'multipart' in r[1] and 'multipart' not in best[2]:
                    best = (path, vendor, r[1])
                    break
                elif 'image/' in r[1] and 'image/' not in best[2]:
                    best = (path, vendor, r[1])
        if best:
            return (i, host, port, best[0], best[1], best[2])
        return None

    completed = 0
    with ThreadPoolExecutor(max_workers=30) as ex:
        for result in ex.map(probe_target, targets):
            completed += 1
            if result:
                i, host, port, path, vendor, ct = result
                key = f'{host}:{port}'
                if key not in tested:
                    tested[key] = {}
                video_url = f'http://{host}:{port}{path}'
                tested[key]['video'] = video_url
                tested[key]['ct'] = ct
                tested[key]['vendor'] = vendor
                upgraded_rows.append((i, video_url, vendor, ct, key))
                found_videos.append((video_url, vendor, ct))
                upgraded += 1
            if completed % 100 == 0:
                progress['tested'] = tested
                progress['upgraded'] = upgraded
                progress['videos'] = found_videos[-100:]
                with open(PROGRESS_PATH, 'w') as f:
                    json.dump(progress, f, indent=2)
                print(f'  [{completed}/{len(targets)}] upgraded={upgraded}', flush=True)

    progress['tested'] = tested
    progress['upgraded'] = upgraded
    progress['videos'] = found_videos
    with open(PROGRESS_PATH, 'w') as f:
        json.dump(progress, f, indent=2)

    print(f'\n[Video V2] Found {upgraded} video streams')

    if upgraded_rows:
        for i, video_url, vendor, ct, key in upgraded_rows:
            rows[i]['live_stream_url'] = video_url
            if 'multipart' in ct:
                rows[i]['type'] = 'video-mjpeg'
            elif 'image/' in ct:
                rows[i]['type'] = 'video'  # It's a faster refresh image
            else:
                rows[i]['type'] = 'video'
            notes = rows[i].get('notes', '') or ''
            rows[i]['notes'] = notes + f' | v2_video={video_url} ct={ct}'

        with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
            w.writeheader()
            w.writerows(rows)
        print(f'  Updated {upgraded_rows.__len__()} rows in CSV')


if __name__ == '__main__':
    main()
