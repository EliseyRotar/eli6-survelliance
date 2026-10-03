"""Find private/undiscovered cam sources.

Multiple approaches:
1. RTSP/ONVIF discovery on residential IP ranges
2. Masscan-style port scan on cam ports (554, 80, 8080, 443)
3. ONVIF WS-Discovery multicast
4. Use a list of known default-credential endpoints
5. Search for "cam", "IPcam", "webcam" in Shodan/Censys results
6. Dark web .onion cams (Tor)
7. FTP/anonymous cam servers
8. Webcams with directory listing
"""
import os
import re
import time
import json
import socket
import urllib.request
import ssl
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


# Common ports that cams use
CAM_PORTS = [
    80, 443, 8080, 8081, 8443,  # Web interface
    554, 8554,  # RTSP
    34567, 34599,  # Some DVRs
    8899,  # DVR web
    10510,  # Some cams
    37777, 37778,  # Dahua
    34567,  # TP-Link
    8000, 8088,  # Various
    5000, 5001,  # Various
    8888, 808, 8082,  # Various
    10000, 10001,  # Webmin-like
    60000, 60001,  # Some cams
]

# Endpoints to probe on a cam web server
PROBE_PATHS = [
    '/', '/index.html', '/cgi-bin/main-cgi', '/cgi-bin/hi3510',
    '/ISAPI/System/deviceInfo', '/ISAPI/Streaming/channels/101',
    '/onvif/device_service', '/onvif-http/snapshot',
    '/Streaming/tracks/101', '/streaming/tracks/101',
    '/cam/realmonitor', '/cam0_0', '/live/0/main',
    '/live/0/sub', '/live/main', '/live/sub',
    '/axis-cgi/mjpg/video.cgi', '/axis-cgi/jpg/image.cgi',
    '/cgi-bin/viewer/video.jpg', '/cgi-bin/faststream.jpg',
    '/-wvhttp-01-/image.cgi', '/image.jpg', '/snapshot.jpg',
    '/video', '/video.mjpg', '/mjpg/video.mjpg', '/video.cgi',
    '/jpg/image.jpg', '/cgi-bin/camera', '/cgi-bin/video',
    '/cgi-bin/CGIProxy.fcgi?cmd=snapPicture2', '/api/v1/streams/main',
    '/webcam/', '/cam/', '/viewer/', '/v/Cam1', '/stream1',
    '/hls/stream.m3u8', '/live.m3u8', '/stream.m3u8',
    '/api/cameras', '/api/streams',
    '/h', '/m',  # Some QNAP cams
    '/dms', '/DMS',  # DVRs
    '/playback', '/recording',
    '/live', '/cam1', '/video1',
    '/image', '/jpg', '/still', '/jpeg',
]

# Common cam URL patterns (no-auth)
NO_AUTH_PATHS = [
    '/video.mjpg', '/mjpg/video.mjpg', '/axis-cgi/mjpg/video.cgi',
    '/cgi-bin/mjpg/video.cgi', '/cgi-bin/viewer/video.jpg',
    '/cgi-bin/faststream.jpg', '/live/main', '/live/sub',
    '/live/0/main', '/live/0/sub', '/live.sdp', '/live.m3u8',
    '/streaming/channels/101', '/Streaming/tracks/101',
    '/stream1', '/stream2', '/h264', '/h264/ch1/main/av_stream',
    '/image', '/image.jpg', '/snapshot', '/snapshot.jpg',
    '/cam_1.cgi', '/videostream.cgi', '/video.cgi',
    '/goform/video', '/goform/snapshot',
    '/ISAPI/Streaming/channels/101',
    '/hls/stream.m3u8', '/stream.m3u8', '/live.m3u8',
]


def probe_url(url, timeout=5, max_bytes=4096):
    """Probe a URL. Returns (status, ct, size)."""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0',
            'Accept': '*/*',
        })
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            data = r.read(max_bytes)
            return (r.status, r.headers.get('Content-Type', ''), len(data))
    except urllib.error.HTTPError as e:
        return (e.code, '', 0)
    except Exception:
        return (-1, '', 0)


def is_cam_url(url, status, ct, size):
    """Determine if a URL is a cam endpoint."""
    if status == 401:
        return True, 'auth_required'  # Cam exists but needs auth
    if status in (200, 301, 302):
        if any(x in ct.lower() for x in ['image', 'video', 'mjpeg', 'mpegurl', 'mp4', 'octet']):
            return True, ct
        if any(x in url.lower() for x in ['cam', 'video', 'mjpeg', 'stream', 'image', 'snapshot', 'live']):
            if size > 1000:
                return True, ct
    return False, ''


# Port scan with cam detection
def scan_host(host, port, timeout=3):
    """Quick port scan + cam probe."""
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return True
    except:
        return False


# Main: Use residential IP ranges and probe for open cam ports
def main():
    print('[Private] This is just a placeholder for now', flush=True)


if __name__ == '__main__':
    main()
