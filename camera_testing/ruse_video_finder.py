"""Find VIDEO versions of Ruse cams.

For each cam URL found, test video stream patterns:
- RTSP path variations
- MJPEG multipart
- HLS /m3u8
- Apple HLS
- Direct MP4
- WebSocket streaming
- Per brand-specific video paths
"""

import os
import csv
import json
import time
import socket
import re
import urllib.request
import urllib.error
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed

WORKDIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
OUT_DIR = os.path.join(WORKDIR, "dossier_ruse", "video_streams")
os.makedirs(OUT_DIR, exist_ok=True)

# Ruse cam URLs to test for video versions
URLS_TO_CHECK = [
    "http://info.weather.yandex.net/20758/3.png",  # Yandex - probably has video!
    "https://images-webcams.windy.com/15/1597690315/current/full/1597690315.jpg",
    "https://images-webcams.windy.com/15/1793898215/current/full/1793898215.jpg",
    "https://images-webcams.windy.com/97/1793902097/current/full/1793902097.jpg",
    "https://www.img.worldcam.pl/webcams/200x113/2026-08-25/14906.jpg",
    "https://www.img.worldcam.pl/webcams/200x113/2026-08-25/24496.jpg",
    "https://www.img.worldcam.pl/webcams/200x113/2026-08-25/2706.jpg",
    "https://www.img.worldcam.pl/webcams/200x113/2026-08-25/37360.jpg",
    "https://www.img.worldcam.pl/webcams/200x113/2026-08-25/40580.jpg",
    "https://cdn.webcamera24.com/static/image/camera/detail/8438-omv-bala-uastreaming/",
    "https://webcamsbg.com/cams/ruse-street.jpg",
]


def check_video_patterns(base_url, hostname=None):
    """Try video stream patterns relative to base_url."""
    if hostname is None:
        m = re.match(r'https?://([^/]+)', base_url)
        hostname = m.group(1) if m else ''

    candidates = []

    # Strip base path
    parsed_path = re.sub(r'\.(jpg|jpeg|png|m3u8|mp4|mjpg|mjpeg)$', '', base_url.split('/', 3)[-1] if '/' in base_url else base_url)
    base_no_ext = base_url.rsplit('.', 1)[0] if '.' in base_url.split('/')[-1] else base_url

    # RTSP paths for common streamers
    rtsp_paths = [
        '/live/main/av_stream',  # Dahua/Hikvision
        '/live/sub/av_stream',
        '/Streaming/tracks/101',  # Hikvision
        '/av0_0', '/av0_1',
        '/Streaming/channels/101',
        '/cam/realmonitor',
        '/cam0_0',
        '/axis-cgi/mjpg/video.cgi',  # AXIS
        '/mjpg/video.mjpg',
        '/videostream.cgi',
        '/11',  # Hipcam
        '/live/0/main',
        '/live/ch00_0',  # HiSilicon
        '/pssia/Streaming/channels/101',  # Uniview
        '/live/ch1',
        '/live/0/av0',
        '/live.sdp',
        '/live',
    ]

    # RTSP/SRT paths
    rtsp_urls = [
        f'rtsp://{hostname}/live/main/av_stream',
        f'rtsp://{hostname}/Streaming/tracks/101',
        f'rtsp://{hostname}/Streaming/channels/101',
        f'rtsp://{hostname}/axis-cgi/mjpg/video.cgi',
        f'rtsp://{hostname}/mjpg/video.mjpg',
        f'rtsp://{hostname}/11',
        f'rtsp://{hostname}/live/0/main',
        f'rtsp://{hostname}/h264',
        f'rtsp://{hostname}/live/ch00_0',
        f'rtsp://{hostname}/live/ch1',
        f'rtsp://{hostname}/pssia/Streaming/channels/101',
        f'rtsp://{hostname}/live.sdp',
    ]

    # HTTP MJPEG/video paths (replace last segment of path)
    http_videos = []
    # Replace 'image.jpg' with various video patterns
    path_patterns = [
        '/mjpg/video.mjpg',
        '/axis-cgi/mjpg/video.cgi',
        '/Streaming/channels/1/picture',
        '/Streaming/tracks/101',
        '/cam/realmonitor?channel=1&subtype=0',
        '/cgi-bin/mjpg/video.cgi?channel=1&subtype=1',
        '/cgi-bin/hi3510/snap.cgi?&-getstream=1',
        '/live/0/main/av0',
        '/live.m3u8',
        '/playlist.m3u8',
        '/hls/live.m3u8',
        '/live/0/video.m3u8',
        '/stream/stream.m3u8',
        '/index.m3u8',
        '/PSIA/Streaming/channels/1',
        '/live/main/av_stream',
        '/live/sub/av_stream',
        '/video.mp4',
        '/videostream.cgi',
    ]

    for path in path_patterns:
        full = f'http://{hostname}{path}'
        http_videos.append(full)

    return rtsp_urls, http_videos


def probe_url(url, timeout=8):
    """Probe a URL and return status info."""
    try:
        if url.startswith('rtsp://'):
            # RTSP probe (raw socket)
            from urllib.parse import urlparse
            parsed = urlparse(url)
            host = parsed.hostname
            port = parsed.port or 554
            path = parsed.path
            sock = socket.create_connection((host, port), timeout=timeout)
            req = f'DESCRIBE {url} RTSP/1.0\r\nCSeq: 1\r\nUser-Agent: Mozilla/5.0\r\n\r\n'
            sock.send(req.encode())
            data = b''
            sock.settimeout(timeout)
            try:
                while b'\r\n\r\n' not in data and len(data) < 4096:
                    d = sock.recv(1024)
                    if not d: break
                    data += d
            except: pass
            sock.close()
            if b'200 OK' in data[:300]:
                # Parse content type from RTSP response
                m = re.search(rb'Content-Type:\s*([^\r\n]+)', data, re.I)
                ct = m.group(1).decode() if m else 'unknown'
                return ('RTSP', 200, ct, data[:200].decode('utf-8', errors='replace'))
            elif b'401' in data[:300]:
                return ('RTSP', 401, 'auth_required', '')
            elif b'404' in data[:300]:
                return ('RTSP', 404, 'not_found', '')
        else:
            # HTTP probe
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'video/*, multipart/*'})
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                data = r.read()
                ct = r.headers.get('Content-Type', '')
                return ('HTTP', r.status, ct, f'{len(data)} bytes')
    except urllib.error.HTTPError as e:
        return ('HTTP', e.code, '', '')
    except Exception as e:
        emsg = str(e)[:50]
        return ('ERR', None, '', emsg)
    return ('UNKNOWN', None, '', '')


def find_videos_for_url(base_url):
    """Find all VIDEO versions of a given base cam URL."""
    print(f'\n=== Testing {base_url[:80]} ===')

    m = re.match(r'https?://([^/]+)', base_url)
    if not m:
        return []
    hostname = m.group(1)

    rtsp_urls, http_videos = check_video_patterns(base_url, hostname)
    print(f'  RTSP candidates: {len(rtsp_urls)}')
    print(f'  HTTP videos: {len(http_videos)}')

    results = []

    # Try RTSP URLs
    for url in rtsp_urls:
        scheme, status, ct, body = probe_url(url)
        if status == 200 and ('video' in ct.lower() or 'octet' in ct.lower() or 'sdp' in ct.lower()):
            results.append({'url': url, 'scheme': scheme, 'status': status, 'content_type': ct, 'body': body[:200]})
            print(f'    [RTSP 200] {url} - {ct}')
        elif status == 200:
            # RTSP 200 but unclear content type
            if 'RTSP/1.0 200' in body:
                results.append({'url': url, 'scheme': scheme, 'status': status, 'content_type': ct, 'body': body[:200]})
                print(f'    [RTSP 200] {url} - body: {body[:80]}')

    # Try HTTP videos
    for url in http_videos:
        scheme, status, ct, body = probe_url(url, timeout=5)
        if status == 200 and ('mpeg' in ct.lower() or 'video' in ct.lower() or 'multipart' in ct.lower() or 'octet' in ct.lower() or 'h264' in ct.lower() or 'mp4' in ct.lower() or 'hls' in ct.lower()):
            results.append({'url': url, 'scheme': scheme, 'status': status, 'content_type': ct, 'body': body[:200]})
            print(f'    [HTTP 200] {url} - {ct}')

    # Also test Yandex's other formats (.mp4 .m3u8)
    m = re.match(r'(https?://[^/]+/(\d+)/)\d+\.png', base_url)
    if m:
        cam_id = m.group(2)
        yandex_base = m.group(1)
        for ext in ['mp4', 'm3u8', 'webm']:
            test = f'{yandex_base}2.{ext}'
            scheme, status, ct, body = probe_url(test, timeout=5)
            if status == 200:
                results.append({'url': test, 'scheme': scheme, 'status': status, 'content_type': ct, 'body': body[:200]})
                print(f'    [Yandex] {test} - {ct}')

    return results


def try_yandex_video():
    """Yandex has a dedicated video API."""
    print('\n=== Try Yandex video API ===')
    for cam_id in [20758]:
        # Yandex has video URL pattern: https://video.{server}/<cam_id>/<size>.mp4
        for s in [1, 2, 3]:
            for ext in ['mp4', 'webm', 'm3u8']:
                # Try various Yandex video URLs
                urls = [
                    f'https://frontend.vh.yandex/player/{cam_id}',
                    f'https://yandex.com/cams/{cam_id}',
                    f'https://video.cdn.yandex/{cam_id}/{s}.mp4',
                    f'https://info.weather.yandex.net/{cam_id}/{s}.mp4',
                    f'https://info.weather.yandex.net/{cam_id}.mp4',
                ]
                for url in urls:
                    scheme, status, ct, body = probe_url(url, timeout=5)
                    if status == 200:
                        print(f'  Yandex {cam_id}/{s}.{ext}: {status} {ct[:50]}')


def try_obscure_video_apis():
    """Try Windy/Yandex/Worldcam API endpoints."""
    print('\n=== Try Windy video endpoints ===')
    for wid in [1597690315, 1793898215, 1793902097]:
        # Windy webcam detail page returns metadata and embed URL
        # The actual stream URL is fetched dynamically
        urls = [
            f'https://node.windy.com/webcam/{wid}/forecast',
            f'https://webcams.windy.com/api/v3/webcam/{wid}',
            f'https://www.windy.com/-Webcam/cam/{wid}',
        ]
        for url in urls:
            try:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=8, context=ctx) as r:
                    data = r.read().decode('utf-8', errors='replace')
                    # Look for video URL or stream
                    player_patterns = re.findall(r'(?:file|src):\s*[\'"]([^\'"]+)[\'"]', data)
                    for p in player_patterns:
                        print(f'    Windy video player file: {p[:100]}')
            except Exception:
                pass


def main():
    print(f'[Video Finder] Starting...')
    all_videos = {}

    # Test each Ruse cam URL
    for url in URLS_TO_CHECK:
        try:
            results = find_videos_for_url(url)
            if results:
                all_videos[url] = results
        except Exception as e:
            print(f'  Error for {url}: {e}')

    # Yandex specific
    try_yandex_video()
    try_obscure_video_apis()

    # Save
    out_path = os.path.join(OUT_DIR, 'video_streams.json')
    with open(out_path, 'w') as f:
        json.dump(all_videos, f, indent=2)
    print(f'\n[Video Finder] Done. {len(all_videos)} cams with videos found')
    print(f'  Saved: {out_path}')


if __name__ == '__main__':
    import urllib.request
    main()
