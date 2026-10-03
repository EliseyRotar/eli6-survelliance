"""Video Stream Upgrader - find VIDEO versions of image cams.

Many "image" cams (single JPEG) have VIDEO versions on the same URL
or alternate ports/paths. This script probes each image cam and tries
to find video streams.

Strategy:
1. For each image cam, try common VIDEO path patterns:
   - /axis-cgi/mjpg/video.cgi (AXIS MJPEG)
   - /mjpg/video.mjpg (generic)
   - /-wvhttp-01-/video (Canon VB MJPEG)
   - /Streaming/tracks/101 (Hikvision)
   - /cam/realmonitor (Dahua)
   - /onvif-http/... (Hikvision CVE-2017-7921)
   - /live/... (Dahua)
2. Check if the response is multipart/x-mixed-replace or video/mp4
3. If found, add video stream URL to the row's live_stream_url
"""
import os
import csv
import re
import time
import json
import socket
import random
import urllib.request
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed

WORKDIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
CSV_PATH = os.path.join(WORKDIR, "controllable_Webcams.csv")
PROGRESS_PATH = os.path.join(WORKDIR, "camera_testing", "video_upgrade_progress.json")

# Find correct path
import glob
if not os.path.exists(CSV_PATH):
    for f in glob.glob(r'C:\Users\eli6-admin\Documents\**/controllable_Webcams.csv', recursive=True):
        CSV_PATH = f
        WORKDIR = os.path.dirname(CSV_PATH)
        PROGRESS_PATH = os.path.join(WORKDIR, "camera_testing", "video_upgrade_progress.json")
        print(f'[Auto-detected] CSV at {CSV_PATH}')
        break

# Common video paths to try
VIDEO_PATHS = [
    # AXIS
    ('/axis-cgi/mjpg/video.cgi', 'AXIS', 'multipart'),
    ('/axis-cgi/video.cgi', 'AXIS', 'video'),
    # Generic
    ('/mjpg/video.mjpg', 'Generic', 'multipart'),
    ('/video.mjpg', 'Generic', 'multipart'),
    ('/video.cgi', 'Generic', 'video'),
    # Canon VB (WV-HTTP)
    ('/-wvhttp-01-/getoneshot?image=img', 'Canon', 'jpeg'),
    ('/-wvhttp-01-/image.cgi', 'Canon', 'jpeg'),
    # Hikvision ISAPI
    ('/Streaming/tracks/101', 'Hikvision', 'video'),
    ('/Streaming/tracks/102', 'Hikvision', 'video'),
    ('/Streaming/channels/1/picture', 'Hikvision', 'jpeg'),
    ('/ISAPI/Streaming/channels/1/picture', 'Hikvision', 'jpeg'),
    ('/onvif-http/snapshot?auth=YWRtaW46MTEK', 'Hikvision', 'jpeg'),
    # Dahua
    ('/cam/realmonitor?channel=1&subtype=0', 'Dahua', 'multipart'),
    ('/cam/realmonitor?channel=1&subtype=1', 'Dahua', 'multipart'),
    ('/cgi-bin/magicBox.cgi', 'Dahua', 'xml'),
    # HiSilicon
    ('/webcam.cgi', 'HiSilicon', 'jpeg'),
    # RTSP variants
    ('/live/0/main', 'Generic', 'rtsp'),
    ('/live/main/av_stream', 'Dahua', 'rtsp'),
    ('/live/0/av0', 'Generic', 'rtsp'),
    ('/h264', 'Generic', 'rtsp'),
    ('/av0_0', 'Generic', 'rtsp'),
    # HLS
    ('/live.m3u8', 'Generic', 'hls'),
    ('/hls/live.m3u8', 'Generic', 'hls'),
    ('/index.m3u8', 'Generic', 'hls'),
    ('/playlist.m3u8', 'Generic', 'hls'),
    # WebcamXP
    ('/cam_1.cgi', 'WebcamXP', 'multipart'),
    ('/cam_2.cgi', 'WebcamXP', 'multipart'),
    # Blue Iris
    ('/image', 'BlueIris', 'jpeg'),
    # Various
    ('/video', 'Generic', 'video'),
    ('/stream', 'Generic', 'video'),
    ('/live', 'Generic', 'video'),
    ('/videostream.cgi', 'Generic', 'video'),
    # i-PRO / Panasonic
    ('/Streaming/ext/Channels/101', 'i-PRO', 'video'),
    ('/LiveCam/Stream', 'i-PRO', 'video'),
    # Sony
    ('/image/1/jpeg.cgi', 'Sony', 'jpeg'),
    ('/viewer/live/0/0', 'Sony', 'jpeg'),
    # Mobotix
    ('/control/faststream.jpg?stream=full', 'Mobotix', 'jpeg'),
]


def probe_video(host, port, path, timeout=4):
    """Try video URL. Returns (status, content_type, is_video) or None."""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        req = f'GET {path} HTTP/1.0\r\nHost: {host}\r\nUser-Agent: Mozilla/5.0\r\nConnection: close\r\n\r\n'
        sock.send(req.encode())
        data = b''
        sock.settimeout(timeout)
        try:
            while len(data) < 10000:
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
            is_video = any(s in ct for s in [
                'multipart/x-mixed-replace', 'video/', 'hls', 'mpeg', 'mp4', 'octet-stream',
                'image/jpeg', 'image/jpg', 'image/png'
            ])
            return (200, ct, is_video)
        elif b'401' in data[:500]:
            return (401, '', False)
    except Exception:
        return None
    return None


def probe_url(url, timeout=5):
    """Probe HTTP URL using urllib."""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            data = r.read()
            ct = r.headers.get('Content-Type', '')
            return (r.status, ct, len(data))
    except urllib.error.HTTPError as e:
        return (e.code, '', 0)
    except Exception:
        return None


def main():
    print(f'[Video Upgrader] Reading {CSV_PATH}')
    csv.field_size_limit(2**31 - 1)
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    # Find rows with image type and extract hosts
    image_hosts = {}  # host -> set of URLs to skip
    target_rows = []
    for i, r in enumerate(rows):
        if (r.get('type') or '') != 'image':
            continue
        url = r.get('url', '') or r.get('live_stream_url', '')
        if not url:
            continue
        # Extract host
        m = re.match(r'https?://([^/]+)(/.*)?', url)
        if not m:
            continue
        host_port = m.group(1)
        if host_port in image_hosts and url in image_hosts[host_port]:
            continue
        image_hosts.setdefault(host_port, set()).add(url)
        target_rows.append((i, host_port, r))

    print(f'  {len(target_rows)} image rows to probe')

    # Progress tracking
    progress = {}
    if os.path.exists(PROGRESS_PATH):
        try:
            with open(PROGRESS_PATH) as f:
                progress = json.load(f)
        except:
            progress = {'tested': {}, 'upgraded': 0}
    tested = progress.get('tested', {})

    upgraded = 0
    upgraded_rows = []

    def probe_host(args):
        i, host_port, row = args
        if host_port in tested and tested[host_port].get('done'):
            return None
        # Parse host:port
        if ':' in host_port:
            host, port = host_port.rsplit(':', 1)
            try:
                port = int(port)
            except:
                port = 80
        else:
            host = host_port
            port = 80

        best_result = None
        for path, vendor, kind in VIDEO_PATHS:
            r = probe_video(host, port, path, timeout=3)
            if r and r[0] == 200 and r[2]:  # is_video True
                if not best_result or len(r[1]) > len(best_result[1]):
                    best_result = (path, vendor, r[1])
                    # Prefer multipart (live video) over jpeg
                    if 'multipart' in r[1] or 'video/' in r[1]:
                        break

        if best_result:
            path, vendor, ct = best_result
            video_url = f'http://{host}:{port}{path}'
            return (i, host_port, path, vendor, ct, video_url)
        return None

    # Probe all targets in parallel
    with ThreadPoolExecutor(max_workers=20) as ex:
        completed = 0
        for result in ex.map(probe_host, target_rows[:1000]):  # Limit to 1000 per run
            completed += 1
            if result:
                i, host_port, path, vendor, ct, video_url = result
                if host_port not in tested:
                    tested[host_port] = {}
                tested[host_port]['done'] = True
                tested[host_port]['video'] = video_url
                tested[host_port]['ct'] = ct
                tested[host_port]['vendor'] = vendor
                upgraded_rows.append((i, video_url, vendor, ct))
                upgraded += 1
            if completed % 50 == 0:
                print(f'  [{completed}/{len(target_rows)}] upgraded={upgraded}')

    print(f'\n[Video Upgrader] Found {upgraded} cams with video streams')

    # Save progress
    progress['tested'] = tested
    progress['upgraded'] = upgraded
    with open(PROGRESS_PATH, 'w') as f:
        json.dump(progress, f, indent=2)

    # Apply upgrades to CSV
    if upgraded_rows:
        for i, video_url, vendor, ct in upgraded_rows:
            # Update the row's live_stream_url and type
            rows[i]['live_stream_url'] = video_url
            if 'multipart' in ct:
                rows[i]['type'] = 'video-mjpeg'
            elif 'video/' in ct:
                rows[i]['type'] = 'video'
            elif 'image/' in ct:
                # Just a still image, skip
                continue
            existing_notes = rows[i].get('notes', '') or ''
            rows[i]['notes'] = existing_notes + f' | video_upgrade={video_url}'

        # Save
        with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
            w.writeheader()
            w.writerows(rows)
        print(f'  Updated {upgraded_rows.__len__()} rows in CSV')


if __name__ == '__main__':
    main()
