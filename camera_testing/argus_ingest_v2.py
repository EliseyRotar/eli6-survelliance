"""Argus ingestion v2 — extract embedded image URLs from HTML pages.

For each chunk's cams:
- If feed URL is image-like (jpg/png/jpeg), HEAD-validate and add directly.
- If feed URL is HTML, GET the page, scan for <img src>, <iframe src>, <source srcset>, .mjpg/.m3u8 links pointing to jpg/mp4, then re-resolve those URLs.
- Skip pages that are paywalls / login walls / 404.

Also fix the project_name field so 'www.x.com IP cam (argus)' becomes 'www.x.com webcam (argus)'.
"""
import csv
import json
import os
import re
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')
import csv_writer

from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\argus2_log.txt'

ARGUS_RAW = 'https://raw.githubusercontent.com/GoSlowPoke168/Argus/master/public/cameras.detail'
NUM_CHUNKS = 229
CORE_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\argus_cameras_core.json'


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
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=80, pool_maxsize=200))
    s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=80, pool_maxsize=200))
    s.headers.update({'User-Agent': 'Mozilla/5.0 (compatible; ArgusIngestor/2.0)'})
    return s


def existing_live_urls():
    seen = set()
    if not os.path.exists(CSV_PATH):
        return seen
    with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    for row in rows[1:]:
        u = row[3] if len(row) > 3 else ''
        if u:
            seen.add(u.lower())
    return seen


IMG_URL_RE = re.compile(r'(?:src|href|data-src|data-srcset|srcset)\s*[=:]\s*["\']([^"\']+)', re.I)
JPG_TOKEN_RE = re.compile(r'\.(?:jpe?g|png|mjpg)(?:\?|$)', re.I)
VIDEO_TOKEN_RE = re.compile(r'\.(?:mp4|m3u8|m3u|hls)(?:\?|$)', re.I)
MJPG_PATH_RE = re.compile(r'/mjpeg(?:stream)?|/video|/stream|/cam/|/snapshot\.jpg|/image\.jpg|/webcam\.jpg', re.I)


def extract_inline_image_urls(html, base_url):
    """Find image-like URLs in HTML <img>, <iframe>, <source>."""
    urls = []
    try:
        parsed_base = urllib.parse.urlparse(base_url)
    except Exception:
        return urls
    for m in IMG_URL_RE.finditer(html):
        u = m.group(1)
        if u.startswith('data:') or u.startswith('//'):
            u = 'https:' + u if u.startswith('//') else u
        if not u.startswith('http'):
            try:
                u = urllib.parse.urljoin(base_url, u)
            except Exception:
                continue
        # strip srcset list splits
        u = u.split(' ')[0].split(',')[0]
        ul = u.lower()
        # accept image-ish or video-ish OR path-y
        if JPG_TOKEN_RE.search(ul) or VIDEO_TOKEN_RE.search(ul) or MJPG_PATH_RE.search(ul):
            urls.append(u)
    # also catch any <meta property="og:image" content="...">
    for m in re.finditer(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', html, re.I):
        u = m.group(1)
        if u.startswith('//'):
            u = 'https:' + u
        if not u.startswith('http'):
            u = urllib.parse.urljoin(base_url, u)
        urls.append(u)
    return list(set(urls))[:6]  # cap


def is_paywall(html):
    """Heuristic detection of 'this site is closed/forbidden/for-pay' pages."""
    hl = html.lower()
    return any(t in hl for t in [
        'subscription required', 'sign in to view', 'login to view', 'membership required',
        'please log in to access', 'page not found', 'forbidden',
        'cookies must be enabled', 'access denied', 'abonnement requis',
        'requires javascript', 'incapsula', 'cloudflare',
    ])


def head_is_image_or_video(s, url):
    try:
        r = s.head(url, timeout=5, allow_redirects=True, verify=False)
        if r.status_code >= 400:
            return False, 0, ''
        ct = r.headers.get('Content-Type', '').lower()
        if 'image/' in ct or 'mpeg' in ct or 'mp4' in ct or 'octet-stream' in ct:
            return True, r.status_code, ct
        # Some IPs return text/plain with image bytes
        cl = int(r.headers.get('Content-Length', 0) or 0)
        if cl > 1024 and ('text/plain' in ct or ct == ''):
            return True, r.status_code, ct
        return False, r.status_code, ct
    except Exception:
        return False, 0, ''


def probe_img_content(s, url):
    """For iframe pages — try GET and look for embedded image urls."""
    try:
        r = s.get(url, timeout=10, allow_redirects=True, verify=False, stream=True)
        if r.status_code >= 400:
            return None
        ct = r.headers.get('Content-Type', '').lower()
        if 'html' in ct or ct.startswith('text/'):
            try:
                html = r.text[:600_000]  # cap
            except Exception:
                html = ''
            if is_paywall(html) or len(html) < 100:
                return None
            inner_urls = extract_inline_image_urls(html, url)
            for u in inner_urls:
                ok, code, ict = head_is_image_or_video(s, u)
                if ok:
                    return u
            return None
        if 'image/' in ct or 'mpeg' in ct or 'octet-stream' in ct:
            return url
    except Exception:
        return None
    return None


def fetch_chunk(s, idx):
    url = f'{ARGUS_RAW}/{idx}.json'
    try:
        r = s.get(url, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def load_core():
    with open(CORE_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def process_chunk(s, chunk_idx, core_data, seen, max_workers=10):
    chunk = fetch_chunk(s, chunk_idx)
    if not chunk:
        return 0
    ids = chunk.get('id', [])
    feeds = chunk.get('feed', [])
    streams = chunk.get('stream', [])
    n = len(ids)
    lons = core_data.get('lon', [])
    lats = core_data.get('lat', [])
    added = 0

    # Stage 1: gather candidates (feed + best_inner)
    candidates = []
    for i in range(n):
        cam_id = ids[i]
        if not cam_id:
            continue
        stream_url = streams[i] if i < len(streams) else ''
        feed_url = feeds[i] if i < len(feeds) else ''
        candidates.append((cam_id, i, stream_url or feed_url))

    # Stage 2: probe in parallel
    def probe(c):
        cam_id, local_idx, url = c
        if not url:
            return None
        if url.lower() in seen:
            return None
        # First try HEAD; if it looks like image, use it; else GET and extract inner
        ok, code, ct = head_is_image_or_video(s, url)
        if ok:
            return (cam_id, local_idx, url, ct)
        # try GET + extract inline image
        inner = probe_img_content(s, url)
        if inner:
            return (cam_id, local_idx, inner, 'image/jpeg')
        return None

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(probe, c) for c in candidates]
        for f in as_completed(futures):
            res = f.result()
            if res is None:
                continue
            cam_id, local_idx, live_url, ct = res
            if live_url in seen:
                continue
            seen.add(live_url)

            # build geo from core local_idx
            try:
                lat = lats[local_idx] if local_idx < len(lats) else None
                lon = lons[local_idx] if local_idx < len(lons) else None
            except Exception:
                lat = lon = None

            m = re.match(r'(?:https?|rtsp|rtmp)://([^/:]+)', live_url)
            host = m.group(1) if m else ''
            # strip 'www.'
            proj_name = host
            if proj_name.startswith('www.'):
                proj_name = proj_name[4:]
            proj_name_short = proj_name.split('.')[0] if '.' in proj_name else proj_name

            # classify type
            if '.m3u8' in live_url or '.m3u' in live_url:
                kind = 'hls-multipart'
            elif '.mp4' in live_url or 'stream' in live_url:
                kind = 'mjpeg-multipart'
            else:
                kind = 'jpeg-frame'

            # family = host-derived label
            try:
                fake_res = {
                    'url': live_url,
                    'family': 'argus-public',
                    'stream_kind': kind,
                    'content_type': ct,
                    'content_length': 0,
                    'weight': 25 if 'mjpg' in live_url or 'm3u8' in live_url or 'mp4' in live_url else 8,
                    'host': host,
                    'port': 443 if live_url.startswith('https') else 80,
                    'ssl': live_url.startswith('https'),
                    'http_status': 200,
                }
                geo = {
                    'country': '',
                    'regionName': '',
                    'city': '',
                    'lat': lat or '',
                    'lon': lon or '',
                    'isp': '',
                    'org': 'Argus Public Cams',
                    'as': '',
                    '_latlon': (lat, lon),  # backfill hook
                }
                entry = csv_writer.entry_from_probe(fake_res, {'source': 'argus-v2'}, geo)
                # Patch project_name & description & type
                desc = entry.get('description', '')
                entry['project_name'] = f'{proj_name_short} webcam (argus)'
                entry['type'] = 'image' if kind == 'jpeg-frame' else 'video'
                entry['live_stream_url'] = live_url
                entry['notes'] = (entry.get('notes', '') + f'; argus_id={cam_id}').strip('; ')
                idx = csv_writer.append_one(entry)
                added += 1
            except Exception as e:
                log(f'  err cam={cam_id}: {e}')
    return added


def main():
    log('[init] starting Argus v2 ingestion')
    s = session()
    seen = existing_live_urls()
    log(f'[init] {len(seen)} existing live URLs')
    core = load_core()
    log(f'[core] {core["count"]} cams in Argus core')
    total_added = 0
    for chunk_idx in range(NUM_CHUNKS):
        try:
            n = process_chunk(s, chunk_idx, core, seen, max_workers=12)
            total_added += n
        except Exception as e:
            log(f'  chunk {chunk_idx} err: {e}')
        if (chunk_idx + 1) % 10 == 0:
            log(f'  progress chunk {chunk_idx+1}/{NUM_CHUNKS}, added={total_added}, seen={len(seen)}')
    log(f'[done] total added from Argus: {total_added}')


if __name__ == '__main__':
    main()
