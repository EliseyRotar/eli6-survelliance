"""Deep Ruse cam scan - probes 27 IPs on webcam-specific ports.

For each IP found by Shodan InternetDB:
- Probe port 80 (web admin)
- Probe port 554 (RTSP)
- Probe port 8080-8082 (alternate web)
- Probe /-wvhttp-01-/getoneshot (Canon VB anon)
- Probe /Streaming/tracks/101 (Hikvision H.264)
- Probe /cam/realmonitor (Dahua MJPEG)
- Probe /axis-cgi/mjpg/video.cgi (AXIS)
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
OUT_DIR = os.path.join(WORKDIR, "dossier_ruse", "services")
MASTER_CSV = os.path.join(WORKDIR, "controllable_Webcams.csv")
PROGRESS = os.path.join(WORKDIR, "camera_testing", "ruse_deep_scan_progress.json")

# Cam probe patterns - (path, vendor)
PROBES = [
    ("/", "Root"),
    ("/-wvhttp-01-/getoneshot?image=img", "Canon VB"),
    ("/-wvhttp-01-/image.cgi", "Canon VB"),
    ("/axis-cgi/mjpg/video.cgi", "AXIS"),
    ("/Streaming/tracks/101", "Hikvision"),
    ("/ISAPI/System/deviceInfo", "Hikvision"),
    ("/Streaming/channels/1/picture", "Hikvision"),
    ("/cam/realmonitor?channel=1&subtype=0", "Dahua"),
    ("/cgi-bin/magicBox.cgi", "Dahua"),
    ("/web/admin.html", "Hikvision"),
    ("/mgmt/index.html", "Hikvision"),
    ("/onvif/device_service", "ONVIF"),
    ("/live/main/av_stream", "Hikvision"),
    ("/live/mpeg4", "AXIS"),
]


def probe_one(args):
    host, port, path = args
    try:
        sock = socket.create_connection((host, port), timeout=4)
        req = f'GET {path} HTTP/1.0\r\nHost: {host}\r\nUser-Agent: Mozilla/5.0\r\nConnection: close\r\n\r\n'
        sock.send(req.encode())
        data = b''
        sock.settimeout(4)
        try:
            while len(data) < 8192:
                d = sock.recv(4096)
                if not d: break
                data += d
        except socket.timeout: pass
        sock.close()
        if b'200 OK' in data[:300]:
            ct = ''
            sh = ''
            for line in data.split(b'\r\n')[:20]:
                if line.lower().startswith(b'content-type:'):
                    ct = line[12:].strip().decode('utf-8', errors='replace')
                elif line.lower().startswith(b'server:'):
                    sh = line[7:].strip().decode('utf-8', errors='replace')
                elif line == b'':
                    break
            return {'host': host, 'port': port, 'path': path, 'status': 200, 'content_type': ct, 'server': sh}
        elif b'401' in data[:500]:
            return {'host': host, 'port': port, 'path': path, 'status': 401, 'content_type': '', 'server': ''}
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
            if not url:
                continue
            new_row = {k: '' for k in header}
            new_row['idx'] = str(start)
            new_row['url'] = url
            new_row['live_stream_url'] = url
            new_row['project_name'] = 'ruse_scan'
            new_row['type'] = 'video' if 'mjpg' in url else 'image'
            new_row['enabled'] = '1'
            new_row['live_status'] = row.get('live_status', 'unknown')
            new_row['http_status'] = str(row.get('http_status', ''))
            new_row['content_type'] = row.get('content_type', '')
            new_row['server_header'] = row.get('server_header', '')
            new_row['brand'] = row.get('brand', 'ruse_scan')
            new_row['category'] = 'public_cam'
            new_row['country'] = 'Bulgaria'
            new_row['city'] = 'Ruse'
            new_row['lat'] = '43.82306'
            new_row['lon'] = '25.95389'
            new_row['confidence'] = '0.5'
            new_row['notes'] = f"ruse_scan | {row.get('notes', '')} | {ts}"
            new_row['csv_id'] = f"RUSESCAN-{int(time.time())}-{start}"
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
    except Exception as e:
        if os.path.exists(lock):
            try: os.remove(lock)
            except: pass
        return 0


def main():
    # Load InternetDB results
    internetdb_path = os.path.join(OUT_DIR, "internetdb_results.json")
    if not os.path.exists(internetdb_path):
        print("Run ruse_scan_services.py first")
        return

    with open(internetdb_path) as f:
        results = json.load(f)

    print(f"[Deep Scan] Loaded {len(results)} IPs from InternetDB")

    # Build target list
    targets = []
    for r in results:
        ip = r['ip']
        for port in r.get('ports', []):
            for path, vendor in PROBES:
                if port in [80, 554] or port in [8080, 8081]:
                    targets.append((ip, port, path))

    print(f"[Deep Scan] {len(targets)} probes total")

    probed = []
    with ThreadPoolExecutor(max_workers=40) as ex:
        for r in ex.map(probe_one, targets):
            if r:
                probed.append(r)

    print(f"[Deep Scan] {len(probed)} successful probes")

    # Filter to ones with webcam signature
    cam_results = []
    for r in probed:
        vendor = next((v for p, v in PROBES if r['path'] == p), 'unknown')
        url = f"http://{r['host']}:{r['port']}{r['path']}"
        # Determine vendor from path
        entry = {
            'url': url,
            'host': f"{r['host']}:{r['port']}",
            'live_status': 'live' if r['status'] == 200 else 'auth_required',
            'http_status': r['status'],
            'content_type': r['content_type'],
            'server_header': r['server'],
            'brand': vendor,
            'notes': f"deep_scan {r['path']} (BG)",
        }
        cam_results.append(entry)
        print(f"  {r['host']}:{r['port']}{r['path']} - {r['status']} {vendor[:15]} {r['server'][:30]}")

    # Save
    with open(os.path.join(OUT_DIR, "deep_scan_results.json"), 'w') as f:
        json.dump(cam_results, f, indent=2)

    # Dedupe
    unique_results = []
    seen_urls = set()
    for c in cam_results:
        if c['url'] not in seen_urls:
            seen_urls.add(c['url'])
            unique_results.append(c)

    # Add to CSV (only live)
    live_only = [c for c in unique_results if c['live_status'] == 'live']
    if live_only:
        added = append_to_csv(live_only)
        print(f"[Deep Scan] Added {added} live cams to CSV")

    print(f"[Deep Scan] Done")


if __name__ == "__main__":
    main()
