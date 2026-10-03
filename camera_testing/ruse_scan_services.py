"""Ruse IP port scanner.

Scans BG prefixes from ipdeny, focusing on common webcam/service ports.
Parallel scan with shodan InternetDB lookups to find live services.
"""

import os
import sys
import csv
import json
import time
import socket
import urllib.request
import ssl
import re
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed

WORKDIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
OUT_DIR = os.path.join(WORKDIR, "dossier_ruse", "services")
MASTER_CSV = os.path.join(WORKDIR, "controllable_Webcams.csv")
PROGRESS = os.path.join(WORKDIR, "camera_testing", "ruse_scanner_progress.json")
BG_ZONE = os.path.join(WORKDIR, "dossier_ruse", "ip_ranges", "bg.zone")

# Common webcam/RTSP/IOT ports
PORTS = [80, 443, 554, 8080, 8081, 8000, 8001, 10554, 7070, 7447, 8554, 9999, 5000, 5001]

# Netlas, Shodan, internetdb
INTERESTING = ["cam", "webcam", "rtsp", "hikvision", "dahua", "axis", "hi3510", "hi3516",
               "onvif", "camera", "video", "dvr", "nvr", "ipcam"]

# Load existing URLs
def load_existing():
    urls = set()
    if os.path.exists(MASTER_CSV):
        try:
            csv.field_size_limit(2**31 - 1)
            with open(MASTER_CSV, 'r', encoding='utf-8', errors='replace') as f:
                for row in csv.DictReader(f):
                    if row.get('host'):
                        urls.add(row['host'].rsplit(':', 1)[0])
        except Exception:
            pass
    return urls


def scan_one(args):
    """Scan one (host, port) - returns True if open."""
    host, port = args
    try:
        sock = socket.create_connection((host, port), timeout=2)
        sock.close()
        return (host, port)
    except (socket.timeout, ConnectionRefusedError, OSError):
        return None


def probe_url(url, timeout=6):
    """Quick probe. Returns (status, content_type, server) or None."""
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
            port = 80 if not url.startswith('https') else 443
        sock = socket.create_connection((host, port), timeout=2)
        req = f'GET {path} HTTP/1.0\r\nHost: {host_port}\r\nUser-Agent: Mozilla/5.0\r\nConnection: close\r\n\r\n'
        sock.send(req.encode())
        data = b''
        sock.settimeout(timeout)
        try:
            while len(data) < 5000:
                d = sock.recv(4096)
                if not d: break
                data += d
        except socket.timeout: pass
        sock.close()
        if b'200 OK' in data[:200] or b'401' in data[:200] or b'302' in data[:200]:
            ct = ''
            sh = ''
            title = ''
            for line in data.split(b'\r\n'):
                if line.lower().startswith(b'content-type:'):
                    ct = line[12:].strip().decode('utf-8', errors='replace')
                elif line.lower().startswith(b'server:'):
                    sh = line[7:].strip().decode('utf-8', errors='replace')
                elif line.lower().startswith(b'<title>'):
                    title = line[7:].split(b'</title>')[0].decode('utf-8', errors='replace') if b'</title>' in line else ''
                elif line == b'':
                    break
            return {
                'status': 200 if b'200 OK' in data[:200] else (401 if b'401' in data[:200] else 302),
                'content_type': ct,
                'server': sh,
                'title': title,
            }
    except Exception:
        pass
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


def main():
    if not os.path.exists(BG_ZONE):
        print(f"No bg.zone at {BG_ZONE}")
        return

    existing_hosts = load_existing()
    print(f"[Ruse Scanner] {len(existing_hosts):,} existing hosts in CSV (skip these)")

    progress = {}
    if os.path.exists(PROGRESS):
        try:
            with open(PROGRESS, 'r') as f:
                progress = json.load(f)
        except Exception:
            progress = {"scanned_prefixes": [], "found": []}
    if not progress.get("scanned_prefixes"):
        progress["scanned_prefixes"] = []
    if not progress.get("found"):
        progress["found"] = []

    # Load prefixes
    with open(BG_ZONE) as f:
        prefixes = [l.strip() for l in f if l.strip() and not l.startswith('#')]

    # Filter to /16 or smaller (manageable count of /24s)
    interesting_prefixes = []
    for p in prefixes:
        if '/' not in p:
            continue
        try:
            net = ipaddress.ip_network(p, strict=False)
            if net.num_addresses <= 2048:  # /21 or larger (max 2048 = /21)
                interesting_prefixes.append(p)
        except ValueError:
            pass

    print(f"[Ruse Scanner] {len(interesting_prefixes)} smaller prefixes to scan")

    # First, let Shodan InternetDB do the work
    # Sample random IPs and query InternetDB for free
    print("[InternetDB] Bulk lookup via Shodan InternetDB...")
    sample_ips = []
    for p in interesting_prefixes[:100]:  # Top 100 prefixes
        try:
            net = ipaddress.ip_network(p, strict=False)
            # Get first usable + 1 random in range
            hosts = list(net.hosts())
            if hosts:
                sample_ips.append(str(hosts[0]))
                if len(hosts) > 2:
                    sample_ips.append(str(hosts[len(hosts) // 2]))
        except Exception:
            pass

    print(f"  Sampling {len(sample_ips)} IPs for Shodan InternetDB lookup")
    # Lookup in parallel
    found_internetdb = []
    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(internetdb_lookup, ip): ip for ip in sample_ips}
        for fut in as_completed(futures):
            ip = futures[fut]
            try:
                data = fut.result(timeout=15)
            except Exception:
                data = None
            if data and data.get('ports'):
                # Found open ports!
                ports = data['ports']
                # Filter to only webcam-related ports
                cam_ports = [p for p in ports if p in PORTS]
                if cam_ports:
                    found_internetdb.append({
                        'ip': ip,
                        'ports': cam_ports,
                        'tags': data.get('tags', []),
                        'cpes': data.get('cpes', []),
                        'vulns': data.get('vulns', []),
                    })

    print(f"  InternetDB found {len(found_internetdb)} IPs with cam-port services")

    # Save InternetDB results
    internetdb_path = os.path.join(OUT_DIR, "internetdb_results.json")
    with open(internetdb_path, 'w') as f:
        json.dump(found_internetdb, f, indent=2)

    # Now probe the found IPs
    print(f"\n[Direct Probe] Probing {len(found_internetdb)} IPs...")
    probed_results = []
    for entry in found_internetdb:
        ip = entry['ip']
        # Try default web ports
        for port in [80, 443, 8080, 8081, 8000, 554]:
            url = f'http://{ip}:{port}/'
            r = probe_url(url, timeout=5)
            if r:
                probed_results.append({
                    'ip': ip,
                    'port': port,
                    'url': url,
                    'status': r['status'],
                    'content_type': r['content_type'],
                    'server': r['server'],
                    'title': r['title'],
                    'tags': entry['tags'],
                    'cpes': entry['cpes'],
                })
                print(f"  {ip}:{port} - {r['status']} {r['server'][:30]} {r['title'][:50]}")
                break

    # Save probe results
    with open(os.path.join(OUT_DIR, "probe_results.json"), 'w') as f:
        json.dump(probed_results, f, indent=2)

    # Filter interesting ones for further BF/probe
    interesting = []
    for r in probed_results:
        url_lower = r['url'].lower()
        for kw in INTERESTING:
            if kw in url_lower or kw in (r.get('title') or '').lower() or kw in (r.get('server') or '').lower():
                interesting.append(r)
                break

    print(f"\n[Ruse Scanner] {len(interesting)} interesting cams found")
    with open(os.path.join(OUT_DIR, "interesting_cams.json"), 'w') as f:
        json.dump(interesting, f, indent=2)

    progress["found"] = found_internetdb
    with open(PROGRESS, 'w') as f:
        json.dump(progress, f)

    print(f"\n[Ruse Scanner] Done. {len(found_internetdb)} IPs with services found")
    print(f"  See {OUT_DIR} for details")


if __name__ == "__main__":
    main()
