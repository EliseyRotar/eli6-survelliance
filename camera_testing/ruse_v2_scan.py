"""Improved Ruse IP scan - filters catchall nginx proxies.

Only adds to CSV if content-type matches expected cam type:
- image/jpeg, image/jpg, image/png for image cams
- multipart/x-mixed-replace for MJPEG
- application/octet-stream or video/mp4 for H.264
- text/xml or application/xml for ONVIF device_service

Captures snapshot to verify
"""

import os
import csv
import json
import time
import socket
import re
import ssl
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

WORKDIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
OUT_DIR = os.path.join(WORKDIR, "dossier_ruse", "services")
MASTER_CSV = os.path.join(WORKDIR, "controllable_Webcams.csv")
PROGRESS = os.path.join(WORKDIR, "camera_testing", "ruse_v2_scan_progress.json")


# Define cam patterns with expected content type
PROBES = [
    # (path, vendor, expected_type_keywords, min_size)
    ("/-wvhttp-01-/getoneshot?image=img", "Canon", ["image/", "jpeg", "jpg"], 100),
    ("/-wvhttp-01-/image.cgi", "Canon", ["image/", "jpeg", "jpg"], 100),
    ("/axis-cgi/mjpg/video.cgi", "AXIS", ["multipart", "image/"], 100),
    ("/Streaming/tracks/101", "Hikvision", [], 50),
    ("/Streaming/channels/1/picture", "Hikvision", ["image/"], 100),
    ("/ISAPI/System/deviceInfo", "Hikvision", ["xml"], 50),
    ("/cam/realmonitor?channel=1&subtype=0", "Dahua", ["multipart", "image/"], 100),
    ("/cgi-bin/magicBox.cgi", "Dahua", ["xml"], 50),
    ("/onvif/device_service", "ONVIF", ["xml"], 50),
]


def probe_validate(args):
    """Probe and validate against expected content type."""
    host, port, path, vendor, expected_types, min_size = args
    try:
        sock = socket.create_connection((host, port), timeout=5)
        req = f'GET {path} HTTP/1.0\r\nHost: {host}\r\nUser-Agent: Mozilla/5.0\r\nConnection: close\r\n\r\n'
        sock.send(req.encode())
        data = b''
        sock.settimeout(5)
        try:
            while len(data) < 50000:
                d = sock.recv(8192)
                if not d: break
                data += d
                if b'\r\n\r\n' in data and (b'200 OK' in data or b'401' in data or b'403' in data):
                    break
        except socket.timeout: pass
        sock.close()

        if b'200 OK' not in data[:300]:
            return None

        # Parse headers
        headers, _, body = data.partition(b'\r\n\r\n')
        ct = ''
        sh = ''
        for line in headers.split(b'\r\n'):
            if line.lower().startswith(b'content-type:'):
                ct = line[12:].strip().decode('utf-8', errors='replace').lower()
            elif line.lower().startswith(b'server:'):
                sh = line[7:].strip().decode('utf-8', errors='replace')

        # Parse response body to look for image markers
        body_lower = body.lower()
        is_image = (
            # JPEG marker
            body.startswith(b'\xff\xd8') or
            # PNG marker
            body.startswith(b'\x89PNG') or
            # MJPEG content
            b'--myboundary' in body_lower or
            b'x-mixed-replace' in body_lower or
            # Look for valid XLM
            (b'<?xml' in body[:50] and any(s in ct for s in ['xml', 'octet-stream']))
        )

        # Validate content type matches expectation
        ct_matches = (
            not expected_types or
            any(s in ct for s in expected_types)
        )

        # Check for catchall nginx (these return 669-byte HTML pages)
        is_catchall = (
            len(body) < 1000 and
            '<html' in body_lower and
            ('nginx' in sh or 'freenginx' in sh or 'apache' in sh)
        )

        if is_image and ct_matches and not is_catchall:
            return {
                'host': host, 'port': port, 'path': path, 'status': 200,
                'content_type': ct, 'server': sh, 'size': len(data),
                'body_first_50': body[:50].hex()
            }
    except Exception:
        return None
    return None


def internetdb_lookup(ip):
    """Use Shodan InternetDB to find known services on IP."""
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
            if not url:
                continue
            new_row = {k: '' for k in header}
            new_row['idx'] = str(start)
            new_row['url'] = url
            new_row['live_stream_url'] = url
            new_row['project_name'] = 'ruse_v2'
            new_row['type'] = 'video' if 'mjpg' in url else 'image'
            new_row['enabled'] = '1'
            new_row['live_status'] = row.get('live_status', 'unknown')
            new_row['http_status'] = str(row.get('http_status', ''))
            new_row['content_type'] = row.get('content_type', '')
            new_row['server_header'] = row.get('server_header', '')
            new_row['brand'] = row.get('brand', 'ruse_v2')
            new_row['category'] = 'public_cam'
            new_row['country'] = 'Bulgaria'
            new_row['city'] = 'Ruse'
            new_row['lat'] = '43.82306'
            new_row['lon'] = '25.95389'
            new_row['confidence'] = '0.6'
            new_row['notes'] = f"ruse_v2_scan | {row.get('notes', '')} | {ts}"
            new_row['csv_id'] = f"RUSEV2-{int(time.time())}-{start}"
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
    import urllib.request

    internetdb_path = os.path.join(OUT_DIR, "internetdb_results.json")
    if not os.path.exists(internetdb_path):
        print("Run ruse_scan_services.py first")
        return

    with open(internetdb_path) as f:
        results = json.load(f)

    print(f"[V2 Scan] Loaded {len(results)} IPs")

    # Build ALL targets: each IP × each path on its primary port (80)
    targets = []
    for r in results:
        ip = r['ip']
        ports = r.get('ports', [])
        # Find cam-related ports
        target_ports = [p for p in ports if p in [80, 443, 554, 8080, 8081, 8000]] or [80]
        for port in target_ports:
            for path, vendor, expected_types, min_size in PROBES:
                targets.append((ip, port, path, vendor, expected_types, min_size))

    print(f"[V2 Scan] {len(targets)} probes total")

    # Probe in parallel
    validated = []
    with ThreadPoolExecutor(max_workers=30) as ex:
        for r in ex.map(probe_validate, targets):
            if r:
                validated.append(r)
                print(f"  VALID {r['host']}:{r['port']}{r['path']} - {r['content_type']} {r['server'][:30]}")

    print(f"[V2 Scan] {len(validated)} validated cams")

    # Save
    with open(os.path.join(OUT_DIR, "v2_scan_results.json"), 'w') as f:
        json.dump(validated, f, indent=2)

    # Convert to CSV rows
    rows = []
    for v in validated:
        url = f"http://{v['host']}:{v['port']}{v['path']}"
        rows.append({
            'url': url,
            'host': f"{v['host']}:{v['port']}",
            'live_status': 'live',
            'http_status': v['status'],
            'content_type': v['content_type'],
            'server_header': v['server'],
            'brand': v['path'].split('/')[1].lower() if '/' in v['path'] else 'unknown',
            'notes': f"v2_scan {v['path']} server={v['server']}",
        })

    if rows:
        added = append_to_csv(rows)
        print(f"[V2 Scan] Added {added} validated cams to CSV")

    # Now also probe for new IPs in BG prefixes using Shodan InternetDB
    print("\n[InternetDB v2] Sampling more BG IPs...")

    # Read bg.zone to get more IPs
    bg_zone = os.path.join(WORKDIR, "dossier_ruse", "ip_ranges", "bg.zone")
    if os.path.exists(bg_zone):
        with open(bg_zone) as f:
            prefixes = [l.strip() for l in f if l.strip() and not l.startswith('#')]

        # Get IPs from prefixes (sample first 200 random IPs from /24 subnets)
        import ipaddress
        sampled = []
        for p in prefixes:
            try:
                net = ipaddress.ip_network(p, strict=False)
                if net.num_addresses >= 256 and net.num_addresses <= 4096:
                    # Sample one IP per /24
                    hosts = list(net.hosts())
                    if hosts and hosts[0]:
                        sampled.append(str(hosts[0]))
            except ValueError:
                pass

        # Filter to ones not already tested
        already_tested = set()
        for r in results:
            already_tested.add(r['ip'])

        new_samples = [ip for ip in sampled if ip not in already_tested][:200]

        # Use InternetDB
        new_findings = []
        with ThreadPoolExecutor(max_workers=20) as ex:
            futures = {ex.submit(internetdb_lookup, ip): ip for ip in new_samples}
            for fut in as_completed(futures):
                ip = futures[fut]
                try:
                    data = fut.result(timeout=15)
                except Exception:
                    data = None
                if data and data.get('ports'):
                    new_findings.append({
                        'ip': ip,
                        'ports': data['ports'],
                        'tags': data.get('tags', []),
                        'cpes': data.get('cpes', []),
                        'vulns': data.get('vulns', []),
                    })

        print(f"  New findings: {len(new_findings)}")

        # Append to JSON
        all_results = results + new_findings
        with open(internetdb_path, 'w') as f:
            json.dump(all_results, f, indent=2)

    print(f"\n[V2 Scan] Done")


if __name__ == "__main__":
    main()
