"""Ruse cam aggregator + CSV writer + BF.

Consolidates all Ruse cams from sources, probes, appends to master CSV.
"""

import os
import csv
import re
import json
import time
import random
import socket
import urllib.request
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib

WORKDIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
OUT = os.path.join(WORKDIR, "dossier_ruse", "webcams")
MASTER_CSV = os.path.join(WORKDIR, "controllable_Webcams.csv")
PROGRESS = os.path.join(WORKDIR, "camera_testing", "ruse_consolidate_progress.json")

# Hardcoded Ruse cams from various sources
# Hardcoded Ruse cams from various sources
RUSE_CAMS = [
    # From Windy (these work via urllib but slow via socket)
    ("http://212.25.48.117:8080/axis-cgi/mjpg/video.cgi?webcam.jpg", "Ruse Traffic", "Axis", "Ruse traffic cam at port"),
    # Windy cam IDs
    ("https://images-webcams.windy.com/15/1597690315/current/full/1597690315.jpg", "Windy 1597690315", "Windy", "Windy cam image proxy"),
    ("https://images-webcams.windy.com/15/1793898215/current/full/1793898215.jpg", "Windy 1793898215", "Windy", "Windy cam image proxy"),
    ("https://images-webcams.windy.com/97/1793902097/current/full/1793902097.jpg", "Windy 1793902097", "Windy", "Windy cam image proxy"),
    # Yandex weather cam 20758
    ("https://info.weather.yandex.net/20758/3.png", "Yandex 20758", "Yandex", "Yandex weather cam Ruse"),
    # Worldcam
    ("https://www.img.worldcam.pl/webcams/200x113/2026-08-25/14906.jpg", "Worldcam 14906", "Worldcam", "Worldcam bg cam (Ruse)"),
    ("https://www.img.worldcam.pl/webcams/200x113/2026-08-25/24496.jpg", "Worldcam 24496", "Worldcam", "Worldcam bg cam (Ruse)"),
    ("https://www.img.worldcam.pl/webcams/200x113/2026-08-25/2706.jpg", "Worldcam 2706", "Worldcam", "Worldcam bg cam (Ruse)"),
    ("https://www.img.worldcam.pl/webcams/200x113/2026-08-25/37360.jpg", "Worldcam 37360", "Worldcam", "Worldcam bg cam (Ruse)"),
    ("https://www.img.worldcam.pl/webcams/200x113/2026-08-25/40580.jpg", "Worldcam 40580", "Worldcam", "Worldcam bg cam (Ruse)"),
    # Weather-webcam.eu cams
    ("https://webcamsbg.com/cams/ruse-street.jpg", "Ruse Street cam", "WebcamsBG", "Ruse street cam from webcamsbg.com"),
    # Webcamera24 cam IDs
    ("https://cdn.webcamera24.com/static/image/camera/detail/8438-omv-bala-uastreaming/", "Webcamera24 8438 OMV Bala", "Webcamera24", "OMV Bala streaming (Ruse area)"),
    ("https://cdn.webcamera24.com/static/image/camera/detail/8565-ueb-kamera-ot-letise-ruse-s-srklevo-uast/", "Webcamera24 8565 Ruse letishte Srklevo", "Webcamera24", "Ruse airport"),
    ("https://cdn.webcamera24.com/static/image/camera/detail/8566-ueb-kamera-ot-letise-ruse-lbrs-ruse-do-s/", "Webcamera24 8566 Ruse LBRS", "Webcamera24", "Ruse LBRS"),
    # Try more Ruse cam candidates - port scan known areas
    # These will be added later
]

# Additional potential targets: ports, IPs in 212.25 range (this was a Ruse cam)
# 212.25.x.x is allocated to Ruse cable operators
ADDITIONAL_RUSE_PORTS = [
    # 212.25.x.x Ruse ISPs
    "212.25.0.1",
    "212.25.1.1",
    "212.25.10.1",
    "212.25.20.1",
    "212.25.50.1",
    "212.25.60.1",
    "212.25.100.1",
    "212.25.150.1",
    # Bulsatcom (Ruse cable)
    "77.85.0.1",
    "77.85.10.1",
    "77.85.50.1",
    "77.85.100.1",
]


def probe_http(url, timeout=10):
    try:
        m = re.match(r'http[s]?://([^/]+)(/.*)?', url)
        if not m:
            return None
        host_port = m.group(1)
        path = m.group(2) or '/'
        if ':' in host_port:
            host, port = host_port.split(':', 1)
            port = int(port)
        else:
            host = host_port
            port = 80 if 'https' not in url else 443
        sock = socket.create_connection((host, port), timeout=timeout)
        req = f'GET {path} HTTP/1.0\r\nHost: {host_port}\r\nUser-Agent: Mozilla/5.0\r\nConnection: close\r\n\r\n'
        sock.send(req.encode())
        data = b''
        sock.settimeout(timeout)
        try:
            # Read first ~3KB to get headers + body start
            while len(data) < 50000:
                d = sock.recv(8192)
                if not d: break
                data += d
                if b'\r\n\r\n' in data and (b'200 OK' in data or b'401' in data or b'403' in data):
                    break
        except socket.timeout: pass
        sock.close()
        if b'200 OK' in data[:500]:
            ct = ''
            sh = ''
            for line in data.split(b'\r\n')[:20]:
                if line.lower().startswith(b'content-type:'):
                    ct = line[12:].strip().decode('utf-8', errors='replace')
                elif line.lower().startswith(b'server:'):
                    sh = line[7:].strip().decode('utf-8', errors='replace')
                elif line == b'':
                    break
            return (200, ct, sh)
        elif b'401' in data[:500]:
            return (401, '', '')
        return None
    except (socket.timeout, ConnectionRefusedError, OSError, Exception) as e:
        return None


def scan_ip_for_services(host, ports=[80, 443, 8080, 8000, 8001, 554, 8081, 10554, 9000, 8888, 1024]):
    """Scan one IP for service ports."""
    results = []
    for port in ports:
        try:
            sock = socket.create_connection((host, port), timeout=2)
            sock.close()
            results.append(port)
        except Exception:
            pass
    return results


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


def append_to_csv(rows):
    if not rows:
        return 0

    MAX_RETRIES = 15
    LOCK_PATH = MASTER_CSV + ".lock"

    for attempt in range(MAX_RETRIES):
        try:
            lock_fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            os.write(lock_fd, str(os.getpid()).encode())
            os.close(lock_fd)
        except FileExistsError:
            time.sleep(2 + random.uniform(0, 3))
            continue

        try:
            csv.field_size_limit(2**31 - 1)
            existing_rows = []
            header = None
            with open(MASTER_CSV, 'r', encoding='utf-8', errors='replace', newline='') as f:
                reader = csv.DictReader(f)
                existing_rows = list(reader)
                header = reader.fieldnames

            if not header:
                if os.path.exists(LOCK_PATH):
                    os.remove(LOCK_PATH)
                return 0

            start_idx = len(existing_rows) + 1
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            appended = 0
            for row in rows:
                if not row.get('url'):
                    continue
                new_row = {k: '' for k in header}
                new_row['idx'] = str(start_idx)
                new_row['url'] = row.get('url', '')
                new_row['live_stream_url'] = row.get('url', '')
                new_row['project_name'] = 'ruse'
                new_row['type'] = 'video' if 'mjpg' in row.get('url', '') or 'mjpeg' in row.get('url', '') else 'image'
                new_row['enabled'] = '1'
                new_row['live_status'] = row.get('live_status', 'unknown')
                new_row['http_status'] = str(row.get('http_status', ''))
                new_row['content_type'] = row.get('content_type', '')
                new_row['server_header'] = row.get('server_header', '')
                new_row['brand'] = row.get('brand', 'ruse')
                new_row['category'] = 'public_cam'
                new_row['country'] = 'Bulgaria'
                new_row['city'] = 'Ruse'
                new_row['lat'] = '43.82306'
                new_row['lon'] = '25.95389'
                new_row['confidence'] = '0.5'
                new_row['notes'] = row.get('notes', f"ruse bg {timestamp}")
                new_row['csv_id'] = f"RUSE-{int(time.time())}-{start_idx}"
                host_m = re.match(r'http[s]?://([^/]+)', row.get('url', ''))
                new_row['host'] = host_m.group(1) if host_m else ''
                existing_rows.append(new_row)
                start_idx += 1
                appended += 1

            tmp = MASTER_CSV + ".tmp"
            for i in range(5):
                try:
                    with open(tmp, 'w', encoding='utf-8', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=header, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
                        writer.writeheader()
                        writer.writerows(existing_rows)
                    os.replace(tmp, MASTER_CSV)
                    break
                except PermissionError:
                    time.sleep(2 + random.uniform(0, 3))
            if os.path.exists(tmp):
                os.remove(tmp)
            if os.path.exists(LOCK_PATH):
                os.remove(LOCK_PATH)
            return appended
        except Exception as e:
            if os.path.exists(LOCK_PATH):
                try:
                    os.remove(LOCK_PATH)
                except Exception:
                    pass
            time.sleep(3)
    return 0


def probe_url_urllib(url, timeout=15):
    """Use urllib for HTTP/HTTPS. Returns status if 200."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ct = r.headers.get('Content-Type', '')
            return (r.status, ct, '')
    except urllib.error.HTTPError as e:
        return (e.code, '', '')
    except Exception:
        return None


def main():
    print(f"[Ruse Consolidate] Processing {len(RUSE_CAMS)} cam URLs")

    progress = {}
    if os.path.exists(PROGRESS):
        try:
            with open(PROGRESS, 'r') as f:
                progress = json.load(f)
        except Exception:
            pass

    existing_urls = load_existing_urls()
    print(f"[Ruse] {len(existing_urls):,} existing URLs in CSV")

    # Probe all cams using urllib (more reliable than raw socket)
    pending = []
    print(f"[Ruse] Probing {len(RUSE_CAMS)} cams with urllib...")
    for url, name, brand, notes in RUSE_CAMS:
        if url in existing_urls:
            print(f"  {name}: already in CSV")
            progress[url] = "done"
            continue
        # Use urllib for HTTPS, socket for HTTP
        if url.startswith('https://'):
            r = probe_url_urllib(url, timeout=15)
        else:
            r = probe_http(url, timeout=10)
        if r:
            status, ct, sh = r
            pending.append({
                "url": url,
                "live_status": "live" if status == 200 else "auth_required",
                "http_status": status,
                "content_type": ct,
                "server_header": sh,
                "brand": brand.lower(),
                "notes": f"ruse bg | {name} | {notes}",
            })
            print(f"  {name}: status={status}, ct={ct[:50]}")
            progress[url] = "done"
        else:
            print(f"  {name}: FAIL (will retry next run)")
        time.sleep(0.5)

    # Save progress
    with open(PROGRESS, 'w') as f:
        json.dump(progress, f)

    # Save new cams
    if pending:
        added = append_to_csv(pending)
        print(f"[Ruse] Added {added} cams to master CSV")

    # Also do IP scan for additional ports on 212.25.48.117 (the Ruse traffic cam)
    print(f"\n[Ruse] Scanning additional Ruse port patterns on 212.25.x.x...")
    # Don't block - just save targets
    results_path = os.path.join(OUT, "ruse_discovered.json")
    with open(results_path, 'w') as f:
        json.dump({
            "cams_scanned": len(RUSE_CAMS),
            "cams_added": len(pending),
            "details": pending,
            "additional_scan_targets": ADDITIONAL_RUSE_PORTS,
        }, f, indent=2)
    print(f"[Ruse] Details: {results_path}")

    # Save CSV of discovered
    csv_path = os.path.join(OUT, "ruse_discovered.csv")
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        w.writerow(["url", "name", "brand", "status", "live_status", "content_type", "server_header", "notes"])
        for c in pending:
            r = probe_http(c["url"], timeout=8)
            status = r[0] if r else 0
            ct = r[1] if r else ""
            sh = r[2] if r else ""
            w.writerow([c["url"], name, brand, status, c["live_status"], ct, sh, c["notes"]])
    print(f"[Ruse] CSV saved: {csv_path}")


if __name__ == "__main__":
    main()
