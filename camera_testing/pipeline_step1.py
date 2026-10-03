"""Orchestrator: harvest candidate hosts -> probe for live streams -> geo -> write CSV.

Runs as one or many waves. Stops when target added is reached or all sources exhausted.
"""
import csv
import json
import os
import queue
import random
import re
import socket
import sys
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15'

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
PROBES_DIR = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing'
LOG_PATH = os.path.join(PROBES_DIR, 'pipeline_log.txt')
HARVEST_PATH = os.path.join(PROBES_DIR, 'all_candidates.json')
LIVE_FOUND_PATH = os.path.join(PROBES_DIR, 'live_streams_new.json')


def _session(pool=50):
    s = requests.Session()
    retries = Retry(total=0, backoff_factor=0.1, status_forcelist=[])
    s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=pool, pool_maxsize=pool))
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=pool, pool_maxsize=pool))
    s.headers.update({'User-Agent': UA, 'Accept': '*/*'})
    return s


# ============================================================
# STEP 1: GATHER CANDIDATES
# ============================================================
def gather_existing_hosts():
    if not os.path.exists(CSV_PATH):
        return set()
    with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    hosts = set()
    for row in rows[1:]:
        for cell in row:
            if not cell:
                continue
            for m in re.finditer(r'(https?|rtsp|rtmp)://([a-z0-9\-\.]+)(?::(\d+))?', cell, re.I):
                hosts.add(m.group(2).lower())
                hosts.add(f'{m.group(2).lower()}:{m.group(3) or 80}')
    return hosts


def bing_search(s, q, count=100):
    """Try to scrape Bing HTML search for URLs."""
    urls = set()
    headers = {'Accept-Language': 'en-US,en;q=0.9'}
    try:
        # Bing HTML route
        r = s.get(f'https://www.bing.com/search?q={urllib.parse.quote(q)}', timeout=20, headers=headers)
        if r.status_code == 200:
            for m in re.finditer(r'<a[^>]+href="(https?://[^"]+)"', r.text, re.I):
                u = m.group(1)
                if not any(d in u for d in ('bing.com', 'microsoft.com', 'msn.com', 'live.com', 'google.com')):
                    urls.add(u)
            # IPs
            for m in re.finditer(r'>(\d{1,3}(?:\.\d{1,3}){3})(?::(\d{1,5}))?<', r.text):
                urls.add(f'http://{m.group(1)}:{m.group(2) or 80}')
    except Exception as e:
        log(f'bing {q[:40]} err: {e}')
    return list(urls)


def shodan_internetdb(s, ips):
    """Free: query /shodan/<ip> for each candidate IP (CC, ports, tags)."""
    out = []
    for ip in ips:
        try:
            r = s.get(f'https://internetdb.shodan.io/{ip}', timeout=6)
            if r.status_code == 200:
                out.append((ip, r.json()))
        except Exception:
            pass
    return out


def fetch_ddg_dorks(s, queries):
    """Use DuckDuckGo HTML search instead of Bing (less rate limiting)."""
    out = []
    for q in queries:
        try:
            r = s.get('https://html.duckduckgo.com/html/', params={'q': q, 'kl': 'us-en'},
                      timeout=15)
            if r.status_code != 200:
                continue
            for m in re.finditer(r'<a[^>]+class="result__a"[^>]+href="(https?://[^"]+)"', r.text):
                u = m.group(1)
                if any(d in u for d in ('duckduckgo.com', 'duck.com', 'wikipedia.org')):
                    continue
                out.append(u)
            for m in re.finditer(r'(\d{1,3}(?:\.\d{1,3}){3})(?::(\d{1,5}))?', r.text):
                out.append(f'http://{m.group(1)}:{m.group(2) or 80}')
        except Exception as e:
            log(f'ddg {q[:40]} err: {e}')
        time.sleep(1.5)
    return list(set(out))


def fetch_insecam_mirror(s):
    """insecam.org is a public IP-cam directory (often lagging, sometimes dead)."""
    cams = []
    # Try a few country pages / plain listing
    pages = [
        'http://www.insecam.org/en/bycountry/US/',
        'http://www.insecam.org/en/bycountry/GB/',
        'http://www.insecam.org/en/bycountry/DE/',
        'http://www.insecam.org/en/bycountry/JP/',
        'http://www.insecam.org/en/bycountry/FR/',
        'http://www.insecam.org/en/bycountry/IT/',
        'http://www.insecam.org/en/bycountry/ES/',
        'http://www.insecam.org/en/bycountry/RU/',
        'http://www.insecam.org/en/bycountry/KR/',
        'http://www.insecam.org/en/bycountry/BR/',
        'http://www.insecam.org/en/bycountry/CA/',
    ]
    for page in pages:
        try:
            r = s.get(page, timeout=20)
            if r.status_code != 200:
                continue
            # pulls IP:port and stream URL
            for m in re.finditer(r'<img[^>]+src="(http[^"]*viewer[^"]+)"', r.text, re.I):
                cams.append(m.group(1))
            for m in re.finditer(r'href="(http[^"]*(?:viewer|view|cam)[^"]+)"', r.text, re.I):
                cams.append(m.group(1))
        except Exception as e:
            log(f'insecam {page[-15:]} err: {e}')
        time.sleep(2)
    return cams


def fetch_pulled_links(s):
    """Pull from sites that aggregate public webcams — opentopia, worldcam, etc."""
    out = []
    pages = [
        'https://www.opentopia.com/webcam.php',
        'https://www.webcams.travel/webcams',
        'https://www.earthcam.com/network/',
        'https://www.skylinewebcams.com/en/webcams.html',
        'https://www.webcam-list.com/',
    ]
    for page in pages:
        try:
            r = s.get(page, timeout=20)
            if r.status_code != 200:
                continue
            for m in re.finditer(r'<a[^>]+href="(https?://[^"]+)"[^>]*>(?:cam|webcam|view|stream)', r.text, re.I):
                u = m.group(1)
                if any(d in u for d in ('opentopia.com', 'skylinewebcams.com', 'webcams.travel', 'earthcam.com', 'webcam-list.com')):
                    pass
                else:
                    out.append(u)
        except Exception as e:
            log(f'agg {page[-15:]} err: {e}')
        time.sleep(1)
    return list(set(out))


def fetch_country_lists(s):
    """Pull from known live-cam counter listings (free country feeds)."""
    out = []
    pages = [
        'https://www.opentopia.com/webcam.php?cid=15',  # random
        'https://www.opentopia.com/webcam.php?cid=20',
        'https://www.opentopia.com/webcam.php?cid=30',
        'https://www.opentopia.com/webcam.php?cid=44',
        'https://www.opentopia.com/webcam.php?cid=53',
        'https://www.opentopia.com/webcam.php?cid=70',
        'https://www.opentopia.com/webcam.php?cid=86',
        'https://www.opentopia.com/webcam.php?cid=97',
        'https://www.opentopia.com/webcam.php?cid=104',
        'https://www.opentopia.com/webcam.php?cid=121',
        'https://www.opentopia.com/webcam.php?cid=128',
        'https://www.opentopia.com/webcam.php?cid=139',
        'https://www.opentopia.com/webcam.php?cid=144',
        'https://www.opentopia.com/webcam.php?cid=159',
        'https://www.opentopia.com/webcam.php?cid=164',
        'https://www.opentopia.com/webcam.php?cid=183',
        'https://www.opentopia.com/webcam.php?cid=196',
    ]
    for page in pages:
        try:
            r = s.get(page, timeout=20)
            if r.status_code != 200:
                continue
            for m in re.finditer(r'<img[^>]+src="(https?://[^"\']+\.jpg)"', r.text, re.I):
                out.append(m.group(1).replace('.jpg', ''))
        except Exception as e:
            log(f'opentopia {page[-15:]} err: {e}')
        time.sleep(1)
    return list(set(out))


def host_range_gen(n=200, ranges=None):
    """Generate random IPs in residential ranges (US/EU ISP blocks)."""
    import ipaddress
    ranges = ranges or [
        '24.0.0.0/8',     # Comcast
        '73.0.0.0/8',     # Comcast
        '76.0.0.0/8',     # generic
        '98.0.0.0/8',     # Comcast/Verizon
        '108.0.0.0/8',
        '174.0.0.0/8',
        '50.0.0.0/8',
        '72.0.0.0/8',
        '68.0.0.0/8',
        '84.0.0.0/8',     # Many EU
        '93.0.0.0/8',
        '94.0.0.0/8',
        '85.0.0.0/8',
        '79.0.0.0/8',
        '87.0.0.0/8',
        '88.0.0.0/8',
        '109.0.0.0/8',
        '151.0.0.0/8',
        '176.0.0.0/8',
        '188.0.0.0/8',
        '189.0.0.0/8',
        '190.0.0.0/8',
        '201.0.0.0/8',
        '213.0.0.0/8',
    ]
    out = set()
    nets = [ipaddress.ip_network(r) for r in ranges]
    while len(out) < n:
        net = random.choice(nets)
        try:
            ip = str(net[random.randint(0, min(net.num_addresses, 800000) - 1)])
            out.add(ip)
        except Exception:
            pass
    return list(out)


def port_fuzz_known_cam_ports(s, ips, ports=None):
    """Quick TCP/HTTP probe a few thousand IPs on common webcam ports."""
    ports = ports or [80, 81, 82, 83, 8000, 8001, 8080, 8081, 8088, 8090, 8888, 8889, 9000, 10000, 1024, 1025, 8086, 2020, 8165, 10510, 10520]
    # Probe only when port is open using requests; very slow for 5k*20; cap to n IPs.
    return ips


# ============================================================
# STEP 2: PROBE FOR LIVE STREAMS
# ============================================================
PROBE_PATTERNS = [
    # (path, weight) — higher weight = better (H.264 > MJPEG > JPEG)
    ('/ISAPI/Streaming/channels/101/httppreview', 60),  # Hikvision live preview (H.264+MJPEG)
    ('/ISAPI/Streaming/channels/1/httppreview', 60),
    ('/axis-cgi/media.cgi?container=matroska&videocodec=h264&resolution=1280x720', 55),
    ('/axis-cgi/media.cgi?container=mp4&videocodec=h264', 50),
    ('/axis-cgi/mjpg/video.cgi', 45),
    ('/axis-cgi/mjpeg/video.cgi', 45),
    ('/axis-cgi/media.cgi?container=matroska&videocodec=h265', 55),
    ('/axis-cgi/media.cgi?container=mp4&videocodec=h265', 50),
    ('/axis-cgi/mpeg4/video.cgi', 40),
    ('/cgi-bin/mjpeg?resolution=1280x960&quality=5', 40),
    ('/cgi-bin/faststream.jpg?stream=full&fps=16', 38),
    ('/control/faststream.jpg?stream=full&fps=16', 38),
    ('/faststream.jpg?stream=full&fps=16', 38),
    ('/-wvhttp-01-/video.cgi', 36),
    ('/-wvhttp-01-/GetData.cgi', 36),
    ('/video.cgi', 35),
    ('/cgi-bin/video?cam=N', 35),
    ('/mjpg/video.mjpg', 35),
    ('/mjpeg', 34),
    ('/video.mjpg', 34),
    ('/web/tmpfs/mjpeg', 32),
    ('/web/tmpfs/mjpeg.jpg', 32),
    ('/cam_1.cgi', 30),
    ('/cam_1.mjpg', 30),
    ('/nphMotionJpeg?Resolution=640x480&Quality=Motion', 28),
    ('/img/main.cgi?StreamCmd=Live&Mode=Live&Resolution=640x480', 28),
    ('/cgi-bin/video.cgi', 28),
    ('/ISAPI/Streaming/channels/1/picture', 5),  # JPEG only
    ('/ISAPI/Streaming/channels/101/picture', 5),
    ('/image.jpg', 4),
    ('/snap.jpg', 4),
    ('/web/tmpfs/snap.jpg', 4),
    ('/web/tmpfs/auto.jpg', 3),
    ('/img.jpg', 2),
    ('/temp/temp.jpg', 2),
    ('/', 0),  # default
]


def looks_like_live_stream(headers, body_bytes):
    ct = headers.get('Content-Type', '').lower()
    cl = headers.get('Content-Length', '-1')
    try:
        cl_n = int(cl)
    except Exception:
        cl_n = 0
    if 'multipart/x-mixed-replace' in ct:
        return ('mjpeg-multipart', 50)
    if 'multipart/related' in ct:
        return ('mjpeg-related', 40)
    if 'image/jpeg' in ct and cl_n >= 5000:
        return ('jpeg-large', 10)
    if 'image/jpeg' in ct and body_bytes[:2] == b'\xff\xd8' and len(body_bytes) > 8000:
        return ('jpeg-frame', 5)
    if 'video/' in ct and 'matroska' in ct:
        return ('matroska', 70)
    if 'video/mp4' in ct:
        return ('mp4', 60)
    if 'text/html' in ct and ('mjpeg' in body_bytes[:200].lower().decode('latin-1', errors='ignore')):
        return ('mjpeg-html', 25)
    return (None, 0)


def probe_host(s, host, port, ssl=False, timeout=4.0, probe_neg=0):
    """Probe a single host on common webcam paths. Return best live URL or None."""
    scheme = 'https' if ssl else 'http'
    base = f'{scheme}://{host}:{port}'
    best = None
    best_w = -1
    if probe_neg > 3:
        return None
    # Try high-weight paths first
    ordered = sorted(PROBE_PATTERNS, key=lambda x: -x[1])
    for path, weight in ordered:
        url = base + path
        try:
            r = s.get(url, timeout=timeout, allow_redirects=False, stream=False,
                      verify=False)
            ct = r.headers.get('Content-Type', '').lower()
            cl = r.headers.get('Content-Length', '0')
            try:
                cl_n = int(cl)
            except Exception:
                cl_n = 0
            # Skip obvious redirects to auth/login
            if r.status_code in (301, 302):
                # follow once
                loc = r.headers.get('Location', '')
                if 'login' in loc.lower() or 'auth' in loc.lower():
                    continue
            if r.status_code == 401:
                # auth-required => may still be alive with creds but skip for now
                continue
            if r.status_code == 200:
                chunk = r.content[:8192]
                kind, w = looks_like_live_stream(r.headers, chunk)
                if kind is None:
                    continue
                # boost if weight already from path
                eff = weight + w
                if eff > best_w:
                    best_w = eff
                    best = {
                        'url': url,
                        'family': _classify(path),
                        'stream_kind': kind,
                        'content_type': ct,
                        'content_length': cl_n,
                        'weight': eff,
                        'host': host,
                        'port': port,
                        'ssl': ssl,
                        'http_status': r.status_code,
                    }
                # H.264/MJPEG is confirmed — short-circuit
                if best_w >= 80:
                    return best
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError,
                requests.exceptions.Timeout, requests.exceptions.RequestException,
                Exception):
            pass
    return best


def _classify(path):
    p = path.lower()
    if 'isapi/streaming/channels' in p and 'picture' in p:
        return 'hikvision'
    if 'isapi/streaming/channels' in p:
        return 'hikvision'
    if 'axis-cgi/media' in p:
        return 'axis'
    if 'axis-cgi' in p:
        return 'axis'
    if 'faststream.jpg' in p:
        return 'mjpeg-faststream'
    if 'wvhttp' in p:
        return 'mjpeg-wvhttp'
    if 'cam_' in p:
        return 'webcamxp'
    if 'web/tmpfs/mjpeg' in p:
        return 'hipcam-mjpeg'
    if 'nphmotionjpeg' in p:
        return 'mobotix'
    if 'cgi-bin/video' in p:
        return 'mjpeg'
    if 'mjpg' in p or 'video.mjpg' in p:
        return 'mjpeg-mjpg'
    return 'unknown'


# ============================================================
# STEP 3: GEO + ADD TO CSV
# ============================================================
def geoip(s, host):
    """Free ip-api.com (45 r/min from same IP)."""
    try:
        r = s.get(f'http://ip-api.com/json/{host}?fields=status,country,regionName,city,zip,lat,lon,isp,org,as,host', timeout=8)
        if r.status_code == 200:
            j = r.json()
            if j.get('status') == 'success':
                return j
    except Exception:
        pass
    return {}


def append_to_csv(entries):
    """Append entries to the CSV. Each entry matches the schema (33 cols).
       If live_stream_url present, second CSV row will be created; we'll merge into a single row per cam."""
    if not entries:
        return 0
    with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    header = rows[0]
    # Determine next idx
    max_idx = 0
    for r in rows[1:]:
        try:
            v = int(r[0])
            if v > max_idx:
                max_idx = v
        except Exception:
            pass

    next_idx = max_idx + 1
    written = 0
    for e in entries:
        idx = next_idx + written
        row = []
        row.append(str(idx))
        row.append(e.get('name', f'Discovered cam {idx}'))
        row.append(e.get('root_url', ''))
        row.append(e.get('live_url', ''))
        row.append(_stream_kind_for_csv(e))
        row.append('yes' if e.get('auth_required') else 'no')
        row.append(e.get('auth_user', ''))
        row.append(e.get('auth_pass', ''))
        row.append('True')
        row.append('live')
        row.append(str(e.get('http_status', 200)))
        row.append(e.get('content_type', ''))
        row.append('')
        row.append('')
        row.append(e.get('description', ''))
        geo = e.get('geo', {})
        row.append(e.get('category', ''))
        row.append('')
        row.append('')
        row.append(e.get('brand', ''))
        row.append(e.get('model', ''))
        row.append(geo.get('country', ''))
        row.append(geo.get('regionName', ''))
        row.append(geo.get('city', ''))
        row.append(geo.get('zip', ''))
        row.append(str(geo.get('lat', '')))
        row.append(str(geo.get('lon', '')))
        row.append(geo.get('isp', ''))
        row.append(geo.get('org', ''))
        row.append(geo.get('as', ''))
        row.append('')
        row.append(e.get('host', ''))
        row.append('medium')
        row.append(e.get('notes', ''))
        row.append(f'discovered_{idx:04d}')

        # Clean each cell of \r\n embedded line breaks (CSV rows must be single line)
        row = [c.replace('\r', ' ').replace('\n', ' ').strip() for c in row]
        rows.append(row)
        written += 1

    # Write back with LF
    with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
        for r in rows:
            w.writerow(r)
    return written


def _stream_kind_for_csv(e):
    kind = e.get('stream_kind', '')
    if 'mp4' in kind or 'matroska' in kind:
        return 'video-h264-matroska'
    if 'httppreview' in kind or 'preview' in e.get('live_url', '').lower():
        return 'video-h264-preview'
    if kind == 'mjpeg-multipart':
        return 'video-mjpeg'
    if kind == 'mjpeg-related':
        return 'video-mjpeg'
    if 'jpeg' in kind:
        return 'image'
    return 'video'


# ============================================================
# STEERING
# ============================================================
_log_lock = threading.Lock()


def log(msg):
    with _log_lock:
        try:
            with open(LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(f'[{time.strftime("%H:%M:%S")}] {msg}\n')
        except Exception:
            pass
        print(msg, file=sys.stderr)


def main():
    s = _session()
    existing_hosts = gather_existing_hosts()
    log(f'[init] existing hosts: {len(existing_hosts)}')

    candidates = []  # list of dicts: {host, port, ssl, source, weight}

    # ----------------------------------------------------------
    # Phase 1 — Aggregator scrapers
    # ----------------------------------------------------------
    log('[phase1] Bing / DDG dorks')
    queries = [
        '"/axis-cgi/mjpg/video.cgi" -bing -microsoft',
        '"/cam_1.cgi" -bing -microsoft',
        '"/cgi-bin/faststream.jpg?stream=full" -bing',
        '"/web/tmpfs/snap.jpg" -bing',
        '"/web/tmpfs/mjpeg" -bing',
        '"/ISAPI/Streaming/channels/101/picture" -bing',
        '"/-wvhttp-01-/video.cgi" -bing',
        '"/axis-cgi/media.cgi" -bing',
        '"Hikvision" inurl:image.jpg camera',
        '"Hipcam" inurl:snap.jpg',
        '"Hipcam" webcam residential',
        '"Hipcam" Hi3510 live web cam',
        '"Hipcam" Hi3518 web cam',
        '"HiSilicon" Hi3510 web camera',
        '"HiSilicon" Hi3518 web camera',
        '"server: Hipcam" camera',
        '"webcam 7" live streaming residential',
        '"server: webcam 7" site:opengamecam.com',
        '"server: webcam 5" webcam',
        '"server: webcamXP 5" streaming',
        'inurl:"/cgi-bin/mjpeg" site:webcam',
        'inurl:"/axis-cgi/media.cgi" site:webcam',
        '"cam_2.cgi" "cam_3.cgi" residential',
        'inurl:camera ip webcam',
        '"camera 7" "user admin" webcam',
        'webcam live residential private',
        'ip cam live streaming private home',
        'home "security camera" live stream residential',
        'inurl:"/nphMotionJpeg" webcam',
        'inurl:"/Streaming/channels" "live"',
        'inurl:"/control/faststream.jpg?stream=full"',
        'inurl:"-wvhttp-01-" cam',
        'inurl:"/ISAPI/System/deviceInfo"',
    ]
    urls = fetch_ddg_dorks(s, queries)
    log(f'[phase1] DDG gave {len(urls)} unique URLs')

    # Convert URLs to (host, port, path)
    seen = set()
    for u in urls:
        try:
            p = urllib.parse.urlparse(u)
            if not p.hostname or '.' not in p.hostname:
                continue
            h = p.hostname.lower()
            port_ = p.port or (443 if p.scheme == 'https' else 80)
            ssl_ = (p.scheme == 'https')
            if (h, port_) in seen:
                continue
            seen.add((h, port_))
            if h in existing_hosts or f'{h}:{port_}' in existing_hosts:
                continue
            candidates.append({'host': h, 'port': port_, 'ssl': ssl_, 'path': p.path or '/', 'source': 'ddg'})
        except Exception:
            pass

    # ----------------------------------------------------------
    # Phase 2 — Insecam
    # ----------------------------------------------------------
    log('[phase2] Insecam scrapes')
    try:
        insecam = fetch_insecam_mirror(s)
        log(f'[phase2] Insecam: {len(insecam)} URLs')
        for u in insecam:
            try:
                p = urllib.parse.urlparse(u)
                if not p.hostname:
                    continue
                h = p.hostname.lower()
                port_ = p.port or (443 if p.scheme == 'https' else 80)
                if (h, port_) in seen:
                    continue
                seen.add((h, port_))
                if h in existing_hosts or f'{h}:{port_}' in existing_hosts:
                    continue
                candidates.append({'host': h, 'port': port_, 'ssl': False, 'path': '/', 'source': 'insecam'})
            except Exception:
                pass
    except Exception as e:
        log(f'insecam fatal: {e}')

    # ----------------------------------------------------------
    # Phase 3 — Country page sweeps
    # ----------------------------------------------------------
    log('[phase3] Country page scrapes')
    try:
        countries = fetch_country_lists(s)
        log(f'[phase3] Country URLs: {len(countries)}')
        for u in countries:
            try:
                p = urllib.parse.urlparse(u)
                if not p.hostname:
                    continue
                h = p.hostname.lower()
                port_ = p.port or 80
                if (h, port_) in seen:
                    continue
                seen.add((h, port_))
                if h in existing_hosts or f'{h}:{port_}' in existing_hosts:
                    continue
                candidates.append({'host': h, 'port': port_, 'ssl': False, 'path': '/', 'source': 'opentopia'})
            except Exception:
                pass
    except Exception as e:
        log(f'country fatal: {e}')

    # ----------------------------------------------------------
    # Phase 4 — IP fuzz on residential ranges (NOT random fuzz; instead try
    # common webcam ports on IPs near existing-Hipcam cam IPs).
    # ----------------------------------------------------------
    log('[phase4] Res-IP extrapolations')
    seen_hosts = {c['host'] for c in candidates}
    seen_hosts.update({h for h in existing_hosts})
    # gather neighbouring /24 members from already-seen IPs
    seed_ips = set()
    for h in list(seen_hosts):
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', h):
            parts = h.split('.')
            seed_ips.add(parts[0] + '.' + parts[1] + '.0.0/24')
    # generate per-/24 random hosts
    import ipaddress
    for rng in list(seed_ips)[:50]:
        try:
            net = ipaddress.ip_network(rng, strict=False)
            for _ in range(20):
                ip = str(net[random.randint(1, 254)])
                if ip in seen_hosts:
                    continue
                seen_hosts.add(ip)
                for port in (8080, 80, 8000):
                    candidates.append({'host': ip, 'port': port, 'ssl': False, 'path': '/', 'source': 'neighbor-fuzz'})
        except Exception:
            pass

    log(f'[phase4] total candidates: {len(candidates)}')

    # ----------------------------------------------------------
    # Phase 5 — Probe in parallel
    # ----------------------------------------------------------
    log('[phase5] probing candidates')
    found = []
    lock = threading.Lock()
    proceeded = [0]

    def _probe_one(c):
        url = probe_host(s, c['host'], c['port'], c.get('ssl', False))
        with lock:
            proceeded[0] += 1
            if proceeded[0] % 50 == 0:
                log(f'   [{proceeded[0]}/{len(candidates)}] probed — found so far: {len(found)}')
        if url:
            with lock:
                found.append((c, url))
                log(f'   [HIT] {url["url"]}  ({url["stream_kind"]}, weight {url["weight"]})')

    with ThreadPoolExecutor(max_workers=20) as ex:
        for c in candidates:
            ex.submit(_probe_one, c)
    log(f'[phase5] probed {proceeded[0]}, found {len(found)} live')

    # ----------------------------------------------------------
    # Phase 6 — Geo + append to CSV
    # ----------------------------------------------------------
    log('[phase6] geo + CSV append')
    n_added = 0
    for src, url in found:
        # geo
        geo = {}
        try:
            geo = geoip(s, url['host'])
        except Exception:
            geo = {}
        # make entry
        fam = url.get('family', 'unknown')
        live_url = url['url']
        root = f'{("https" if url["ssl"] else "http")}://{url["host"]}:{url["port"]}'
        entry = {
            'name': f'Live cam on {url["host"]}:{url["port"]}',
            'root_url': root,
            'live_url': live_url,
            'category': 'residential' if 'residential' in (geo.get('org', '') or '').lower() else 'public',
            'brand': '',
            'model': '',
            'host': url['host'],
            'notes': f'Stream kind: {url["stream_kind"]}. Family: {fam}. Source: {src["source"]}.',
            'auth_required': False,
            'http_status': url.get('http_status', 200),
            'content_type': url.get('content_type', ''),
            'stream_kind': url.get('stream_kind', ''),
            'geo': geo,
        }
        n_added += append_to_csv([entry])
        # small sleep to avoid ip-api rate limit
        time.sleep(1.2)

    log(f'[done] CSV +{n_added} rows. {n_added} cams added.')
    return n_added


if __name__ == '__main__':
    main()
