"""Bulk RTSP probe on insecam-discovered cam IPs.

We have ~300+ new MJPEG cams from insecam. Let me also check if any of their
IP-based cam servers also run RTSP. RTSP cams are MUCH more valuable (real video).
"""
import csv
import os
import time
import json
import re
import socket
import urllib.request
import ssl
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

import glob

CSV_PATH = None
for f in glob.glob(r'C:\Users\eli6-admin\Documents\**/controllable_Webcams.csv', recursive=True):
    CSV_PATH = f
    break
if not CSV_PATH:
    print('CSV not found')
    exit(1)
print(f'CSV: {CSV_PATH}')


def fetch(url, timeout=5, max_bytes=4096):
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            data = r.read(max_bytes)
            return r.status, r.headers.get('Content-Type', ''), len(data)
    except urllib.error.HTTPError as e:
        return e.code, '', 0
    except Exception as e:
        return -1, str(e)[:50], 0


# Common RTSP paths
RTSP_PATHS = [
    '/', '/live', '/live.sdp', '/video', '/mpeg4', '/h264',
    '/11', '/12', '/13',  # Hipcam
    '/onvif/streaming/channels/101',  # Sony
    '/Streaming/tracks/101',  # Hikvision
    '/Streaming/Channels/101',  # Dahua
    '/stream1', '/stream2',
    '/av0_0', '/av0_1',  # Uniview
    '/cam/realmonitor',  # Dahua
    '/live/0/main', '/live/0/sub',  # Uniview
    '/trackID=1',  # GeoVision
    '/PSIA/Streaming/channels/101',  # PSIA
    '/video1', '/video2',
    '/ch0_0', '/ch0_1',  # HiSilicon
    '/h264/ch1/main/av_stream', '/h264/ch1/sub/av_stream',  # HiSilicon
    '/0/usrnm:pwd/0', '/1/usrnm:pwd/1',  # AirLive
]


def tcp_probe(host, port, timeout=3):
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        # Try RTSP DESCRIBE
        s.settimeout(timeout)
        s.send(b'OPTIONS rtsp://%s:%d/ RTSP/1.0\r\nCSeq: 1\r\n\r\n' % (host.encode(), port))
        data = s.recv(2048)
        s.close()
        return data.decode('utf-8', errors='replace')
    except Exception as e:
        return None


def main():
    csv.field_size_limit(2**31 - 1)
    existing = set()
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            if row.get('url'):
                existing.add(row['url'])
    print(f'  CSV has {len(existing):,} URLs')

    # Get unique IPs from insecam-style URLs (host:port pattern)
    ips = set()
    for url in existing:
        m = re.match(r'https?://(\d+\.\d+\.\d+\.\d+):?(\d+)?', url)
        if m:
            ip = m.group(1)
            port = int(m.group(2)) if m.group(2) else 80
            ips.add((ip, port))

    # Filter to insecam-style ports
    targets = [(ip, 554) for ip, port in ips if port in (80, 8080, 8081, 8082, 80, 8000, 8001)]
    targets = list(set(targets))
    print(f'  {len(targets)} unique IPs to probe RTSP on port 554')

    # RTSP scan
    print(f'\n[RTSP Scan] Probing {len(targets)} IPs on port 554...')
    found = []
    with ThreadPoolExecutor(max_workers=20) as ex:
        def probe(t):
            ip, port = t
            resp = tcp_probe(ip, port, timeout=3)
            if resp and ('RTSP' in resp or '200 OK' in resp or '404' in resp):
                return (ip, port, resp[:200])
            return None
        futs = {ex.submit(probe, t): t for t in targets[:2000]}
        n_done = 0
        for f in as_completed(futs):
            try:
                r = f.result(timeout=6)
                if r:
                    found.append(r)
            except Exception:
                pass
            n_done += 1
            if n_done % 100 == 0:
                print(f'  {n_done}/{min(2000, len(targets))} probed, {len(found)} found')

    print(f'\n  RTSP endpoints: {len(found)}')
    for ip, port, resp in found[:30]:
        print(f'  {ip}:{port} {resp[:100].strip()}')


if __name__ == '__main__':
    main()
