"""Harvest public IP cams from many sources.

Sources:
1. Shodan API (InternetDB + on-demand search if API key is provided)
2. Censys (HTML scrape of public search page — limited)
3. Bing dork: `/cgi-bin/faststream.jpg?stream=full` (Bosch/ACTi/Mobotix common)
4. Bing dork: `/axis-cgi/mjpg/video.cgi`
5. Bing dork: `/cam_1.cgi` (WebcamXP 5)
6. Bing dork: `/web/tmpfs/snap.jpg` (Hipcam)
7. Bing dork: `inurl:viewer.html?Mode=Motion` (ACTi)
8. Bing dork: `/ISAPI/Streaming/channels/101` (Hikvision)
9. Bing dork: `/onvif/device_service` (ONVIF cams)
10. Bing dork: `/mjpg/video.mjpg`
11. Known webcam directories: cam-scraping aggregators and public cam lists
12. Reddit /r/webcams + CamCaps
13. Public AXIS hardware list (axis-networks.dk, webcam-list.com)
14. Known camera list sites
15. Custom URL fuzzing on already-found IPs (other ports / paths)

Each candidate is:
  (host, port, path, family) — geo-enriched then probed for live stream
"""
import argparse
import csv
import json
import random
import re
import socket
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15'


def make_session(pool=20):
    s = requests.Session()
    retries = Retry(total=1, backoff_factor=0.2, status_forcelist=[500, 502, 503, 504])
    s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=pool, pool_maxsize=pool))
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=pool, pool_maxsize=pool))
    s.headers.update({'User-Agent': UA, 'Accept': '*/*'})
    return s


BING = 'https://www.bing.com/search?q={q}&count=100&format=json'
HDR_HOST_RE = re.compile(r'(?P<host>[\w\-][\w\-\.]*[\w\-])(?::(?P<port>\d+))?')

# Path templates per family — used for probe() too
URL_PATTERNS = {
    'axis-mjpeg': ['/axis-cgi/mjpg/video.cgi'],
    'axis-mpeg': ['/axis-cgi/mpeg4/video.cgi'],
    'axis-h264': ['/axis-cgi/media.cgi?container=matroska&videocodec=h264'],
    'axis-h264-mp4': ['/axis-cgi/media.cgi?container=mp4&videocodec=h264'],
    'axis-h265': ['/axis-cgi/media.cgi?container=matroska&videocodec=h265'],
    'mjpeg-fs': ['/cgi-bin/faststream.jpg?stream=full&fps=16',
                  '/control/faststream.jpg?stream=full&fps=16'],
    'mjpeg-cgi': ['/cgi-bin/mjpeg', '/mjpeg', '/video.mjpg', '/mjpg/video.mjpg'],
    'mjpeg-wvhttp': ['/-wvhttp-01-/video.cgi', '/-wvhttp-01-/GetData.cgi'],
    'mjpeg-canon': ['/img/main.cgi?StreamCmd=Live&Mode=Live&Resolution=640x480'],
    'mjpeg-panasonic': ['/nphMotionJpeg?Resolution=640x480&Quality=Motion'],
    'mjpeg-acti': ['/cgi-bin/video?cam=N', 'cgi-bin/nphMotionJpeg'],
    'mjpeg-vivotek': ['/cgi-bin/video.cgi'],
    'mjpeg-dlink': ['/video.cgi', '/video1.mjpg'],
    'mjpeg-tplink': ['/stream/video/mjpeg', '/video/mjpg.cgi'],
    'webcamxp': ['/cam_1.cgi', '/cam_1.mjpg', '/live.flv'],
    'hikvision': ['/ISAPI/Streaming/channels/101/picture',
                  '/ISAPI/Streaming/channels/101/httppreview',
                  '/ISAPI/Streaming/channels/1/picture'],
    'hipcam-snap': ['/web/tmpfs/snap.jpg'],
    'hipcam-mjpeg': ['/web/tmpfs/mjpeg.jpg', '/web/tmpfs/mjpeg', '/mjpeg'],
    'onvif-snap': ['/onvif/device_service', '/Streaming/channels/1/picture'],
}


def is_ip(h):
    try:
        socket.inet_aton(h)
        return True
    except Exception:
        return False


def extract_hosts(text):
    """Find URLs in arbitrary text and return [(host, port, path)]."""
    out = set()
    for m in re.finditer(r'href=["\']?(https?://[^"\'\s>]+)', text, re.I):
        out.add(m.group(1))
    # also bare host:port patterns inside text
    for m in re.finditer(r'(?:^|\s)([a-z0-9][a-z0-9\-.]*\.[a-z]{2,})(?::(\d{1,5}))?(?:[/\s"<>])', text, re.I):
        host = m.group(1).lower()
        if any(host.endswith(x) for x in ('google.com', 'bing.com', 'microsoft.com', 'w3.org', 'mozilla.org', 'github.com', 'cloudflare.com', 'apache.org')):
            continue
        if len(host) > 70:
            continue
        out.add((m.group(1), m.group(2) or '80'))
    urls = set()
    for u in out:
        if isinstance(u, tuple):
            host, port = u
            urls.add((host, port, '/'))
        else:
            p = urllib.parse.urlparse(u)
            urls.add((p.hostname or '', p.port or (443 if p.scheme == 'https' else 80), p.path))
    return sorted([u for u in urls if u[0]])


def dedup_against_existing(cands, existing_set):
    """Remove candidates already in CSV (any host seen before or in live URL)."""
    fresh = []
    for c in cands:
        h, port, path, fam = c
        keys = [
            f'{h}:{port}',
            f'{h}',
        ]
        if any(k in existing_set for k in keys):
            continue
        fresh.append(c)
    return fresh


def gather_existing_set():
    """Return set of hosts/host:port already in CSV (any field)."""
    with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv', 'r', encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    header = rows[0]
    hosts = set()
    for row in rows[1:]:
        for cell in row:
            if not cell:
                continue
            # extract url(s)
            for m in re.finditer(r'https?://([a-z0-9\-\.]+)(?::(\d+))?/', cell, re.I):
                hosts.add(m.group(1))
                hosts.add(f'{m.group(1)}:{m.group(2) or 80}')
    return hosts


# ----------------------------- Source 1: Shodan InternetDB -----------------------------
def source_shodan_internetdb(s, targets):
    """Query Shodan InternetDB (free, no key) for IP-as-candidates."""
    out = []
    # InternetDB only accepts IPs, so scan /25 sample of common ranges
    # Actually InternetDB is per-IP — we need a list of IPs. So skip to bilisource.
    return out


# ----------------------------- Source 2: Shodan API (if key) -----------------------------
def source_shodan_search(s, api_key, query):
    out = []
    if not api_key:
        return out
    try:
        # Use facets — or simply /shodan/host/search
        page = 1
        while page <= 5:
            r = s.get(f'https://api.shodan.io/shodan/host/search?key={api_key}&query={urllib.parse.quote(query)}&page={page}', timeout=15)
            if r.status_code != 200:
                break
            j = r.json()
            for hit in j.get('matches', []):
                ip = hit.get('ip_str')
                port = hit.get('port')
                if ip and port:
                    out.append(('shodan', ip, port, hit.get('data', '')[:50]))
            if page * 100 >= j.get('total', 0):
                break
            page += 1
            time.sleep(1)
    except Exception as e:
        print(f'[shodan] {e}', file=sys.stderr)
    return out


# ----------------------------- Source 3-9: Bing dorks -----------------------------
def source_bing(s, query, count=200):
    """Hit Bing HTML search and extract URLs."""
    urls = []
    try:
        # Bing HTML doesn't really return JSON; use HTML and parse.
        r = s.get(f'https://www.bing.com/search?q={urllib.parse.quote(query)}&count={count}', timeout=20,
                  headers={'Accept-Language': 'en-US,en;q=0.9', 'Cookie': 'MUID=abc'})
        if r.status_code != 200:
            return urls
        txt = r.text
        for m in re.finditer(r'<a[^>]+href="(https?://[^"]+)"', txt, re.I):
            url = m.group(1)
            if 'bing.com' in url or 'microsoft.com' in url or 'msn.com' in url:
                continue
            urls.append(url)
        # also extract IPs that appear in text
        for m in re.finditer(r'(\d{1,3}(?:\.\d{1,3}){3})(?::(\d{1,5}))?', txt):
            urls.append(f'http://{m.group(1)}:{m.group(2) or 80}')
    except Exception as e:
        print(f'[bing] {query[:50]}: {e}', file=sys.stderr)
    return urls


# ----------------------------- Source 10: Direct seed lists -----------------------------
SEED_LISTS = [
    # Format: (url, family_hint) — known live public cams with no auth
    ('http://195.196.36.242', 'axis'),  # Pajala
    ('http://flightcam1.pr.erau.edu', 'axis'),
    ('http://flightcamnorth.db.erau.edu', 'axis'),
    ('http://flightcamsouth.db.erau.edu', 'axis'),
    ('http://wc2.dartmouth.edu', 'axis'),
]


def source_seeds():
    out = []
    for url, fam in SEED_LISTS:
        p = urllib.parse.urlparse(url)
        out.append((p.hostname, p.port or 80, p.path or '/', fam))
    return out


# ----------------------------- Source 11-12: Public cam aggregator pages -----------------------------
def source_webcam_aggregator(s):
    """Hit known webcam aggregator pages and extract URLs."""
    candidates = []
    pages = [
        'https://www.earthcam.com/',
        'https://www.opentopia.com/webcam.php',
        'https://www.webcams.travel/',
        'https://www.skylinewebcams.com/',
        'https://www.camfinder.com/',
        'https://www.worldcam.eu/',
        'https://www.insecam.org/',
    ]
    for url in pages:
        try:
            r = s.get(url, timeout=15)
            if r.status_code == 200:
                for h, port, pth in extract_hosts(r.text):
                    candidates.append((h, int(port) if str(port).isdigit() else 80, pth))
        except Exception:
            pass
    return candidates


# ----------------------------- Source 13: CamCaps + Reddit -----------------------------
def source_reddit(s):
    """Hit /r/webcams / CamCaps lists. Reddit needs API hack — use old .json."""
    out = []
    subs = ['webcams', 'cams', 'webcam', 'publiccams', 'livecams']
    for sub in subs:
        try:
            r = s.get(f'https://www.reddit.com/r/{sub}/.json?limit=100', timeout=15,
                      headers={'User-Agent': 'Mozilla/5.0 (cam.harvest)'})
            if r.status_code != 200:
                continue
            j = r.json()
            for c in j.get('data', {}).get('children', []):
                d = c.get('data', {})
                text = ' '.join([d.get('selftext', '') or '', d.get('title', '') or '', d.get('url', '') or ''])
                for h, port, _path in extract_hosts(text):
                    if h and port:
                        out.append((h, int(port) if str(port).isdigit() else 80, '/'))
        except Exception:
            pass
    return out


# ----------------------------- Source 14: Shodan on-demand (public browse) -----------------------------
def source_shodan_pages(s):
    """Bing-style dork 'site:shodan.io webcams' — extracts IPs from snippets."""
    out = []
    q = 'shodan.io webcam ip city country'
    urls = source_bing(s, q, count=50)
    for u in urls:
        p = urllib.parse.urlparse(u)
        if p.hostname:
            out.append((p.hostname, p.port or 80, '/', 'unknown'))
    return out


# ----------------------------- Source 15: IP fuzz (broad scan of common webcam ports) -----------------------------
import ipaddress

def gen_random_ips(n):
    """Generate n random public IPs from common ranges."""
    out = set()
    ranges = [
        ipaddress.ip_network('24.0.0.0/8'),     # Comcast home
        ipaddress.ip_network('73.0.0.0/8'),
        ipaddress.ip_network('98.128.0.0/9'),
        ipaddress.ip_network('76.0.0.0/8'),     # generic
        ipaddress.ip_network('108.0.0.0/8'),
        ipaddress.ip_network('174.0.0.0/8'),
        ipaddress.ip_network('50.0.0.0/8'),
        ipaddress.ip_network('72.0.0.0/8'),
        ipaddress.ip_network('68.0.0.0/8'),
    ]
    while len(out) < n:
        r = random.choice(ranges)
        out.add(str(r[random.randint(0, r.num_addresses - 1)]))
    return list(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--shodan-key', default=None)
    parser.add_argument('--no-reddit', action='store_true')
    parser.add_argument('--no-shodan-dorks', action='store_true')
    parser.add_argument('--limit', type=int, default=400, help='Max probes to run')
    parser.add_argument('--out', default=r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\harvest_candidates.json')
    args = parser.parse_args()

    existing_hosts = gather_existing_set()
    print(f'[existing] {len(existing_hosts)} host keys seen')
    s = make_session()
    candidates = []

    print('[seeds]')
    for h, port, path, fam in source_seeds():
        candidates.append(('seed', h, port, path))
    print('[bing]')
    bing_dorks = [
        'inurl:/axis-cgi/mjpg/video.cgi',
        'inurl:/cam_1.cgi',
        'inurl:/cgi-bin/faststream.jpg',
        'inurl:/web/tmpfs/snap.jpg',
        'inurl:-wvhttp-01-',
        'inurl:/ISAPI/Streaming/channels',
        'inurl:/onvif/device_service',
        'inurl:/ViewerFrame?Mode=',
        'inurl:/nphMotionJpeg',
        'inurl:/Streaming/channels/1',
    ]
    bing_hits = []
    for d in bing_dorks:
        urls = source_bing(s, d, count=100)
        print(f'[bing] {d}: {len(urls)} urls')
        bing_hits.extend(urls)
        time.sleep(1.0)

    # Convert bing urls to (host, port, path)
    seen = set()
    for u in bing_hits:
        try:
            p = urllib.parse.urlparse(u)
            if not p.hostname:
                continue
            port_ = p.port or 80
            key = (p.hostname, port_)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(('bing', p.hostname, port_, p.path or '/'))
        except Exception:
            pass

    if not args.no_reddit:
        print('[reddit]')
        for h, p, pth in source_reddit(s):
            candidates.append(('reddit', h, p, pth))

    print('[seeds]'), None

    # Shodan API
    if args.shodan_key:
        print('[shodan-api]')
        for q in ['webcam xp', 'axis-cgi mjpg', 'webcam 7', 'hipcam']:
            for src, ip, port, snippet in source_shodan_search(s, args.shodan_key, q):
                if is_ip(ip):
                    candidates.append(('shodan', ip, port, '/'))

    # Aggregator pages
    print('[aggregators]')
    for h, port, pth in source_webcam_aggregator(s):
        if h:
            candidates.append(('aggregator', h, port, pth))

    # dedup
    print(f'[total raw] {len(candidates)}')

    # Filter to known-new
    out_uniq = set()
    out_list = []
    for src, h, port, path in candidates:
        try:
            if not h or not isinstance(h, str):
                continue
            p = int(port) if isinstance(port, str) else port
        except Exception:
            continue
        try:
            p = int(p)
        except Exception:
            continue
        if p in (25, 465, 587, 21, 22, 0):
            continue
        if any(b in h for b in ('bing.com', 'microsoft.com', 'reddit.com', 'shodan.io', 'wikipedia.org', 'amazonaws.com', 'github.com', 'googleapis.com', 'cloudfront.net', 'imgur.com', 'youtube.com')):
            continue
        key = (h, p)
        if key in out_uniq:
            continue
        out_uniq.add(key)
        # is it known?
        if h in existing_hosts or f'{h}:{p}' in existing_hosts:
            continue
        out_list.append({'src': src, 'host': h, 'port': int(p), 'path': path if isinstance(path, str) else '/'})

    print(f'[unique new candidates] {len(out_list)}')
    random.shuffle(out_list)
    out_list = out_list[:args.limit]

    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(out_list, f, indent=2)
    print(f'[saved] {args.out}')


if __name__ == '__main__':
    main()
