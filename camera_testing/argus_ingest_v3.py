"""Argus ingestion v3 — high-yield, chunked, persistent, parallel.

Improvements over v2:
- Persists chunk progress to JSON (skips already-done chunks on restart)
- 30 threads
- Better inline image extractor: img src/srcset/data-src, picture>source,
  iframe src, .mjpg/.m3u8/.mp4/.jpg anywhere in HTML
- Catches img.onerror("...","http://cam/") JS handlers
- Adds Mozilla/5.0 UA + Accept headers to bypass basic bot blocks
- Tracks per-chunk stats
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
import tier5_extractor

from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\argus3_log.txt'
PROGRESS_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\argus3_progress.json'

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
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=120, pool_maxsize=300))
    s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=120, pool_maxsize=300))
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/jpeg,image/png,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    })
    return s


def existing_live_urls():
    seen = set()
    if not os.path.exists(CSV_PATH):
        return seen
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        rows = list(csv.reader(f))
    for row in rows[1:]:
        if len(row) > 3 and row[3]:
            seen.add(row[3].lower().strip())
    return seen


def existing_argus_ids():
    """Track which Argus IDs are already in CSV via notes field."""
    ids = set()
    if not os.path.exists(CSV_PATH):
        return ids
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        rows = list(csv.reader(f))
    for row in rows[1:]:
        if len(row) > 33 and row[33]:
            for m in re.finditer(r'argus_id=([^\s;,]+)', row[33]):
                ids.add(m.group(1))
    return ids


def load_progress():
    if os.path.exists(PROGRESS_PATH):
        try:
            with open(PROGRESS_PATH, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {'done_chunks': [], 'last_idx': -1}


def save_progress(prog):
    try:
        with open(PROGRESS_PATH, 'w') as f:
            json.dump(prog, f)
    except Exception:
        pass


# Comprehensive inline image extraction
IMG_RE = re.compile(
    r'(?:src|href|data-src|data-srcset|srcset|data-original|data-lazy-src|content)\s*[:=]\s*["\']([^"\']+)',
    re.I
)
JPG_TOKEN_RE = re.compile(r'\.(?:jpe?g|png|mjpg|mjpeg)(?:\?|$)', re.I)
VIDEO_TOKEN_RE = re.compile(r'\.(?:mp4|m3u8|m3u|hls|ts)(?:\?|$)', re.I)
MJPG_PATH_RE = re.compile(r'(?:/mjpeg(?:stream)?|/video|/stream|/cam/|/snapshot\.jpg|/image\.jpg|/webcam\.jpg|/cgi-bin/.*mjpg|/axis-cgi/.*media|/Streaming/.*101|/videostream\.cgi|/mjpgvideo\.cgi|/goform/video|/ISAPI/Streaming/)', re.I)


def extract_inline_image_urls(html, base_url):
    urls = []
    try:
        parsed_base = urllib.parse.urlparse(base_url)
    except Exception:
        return urls
    for m in IMG_RE.finditer(html):
        u = m.group(1)
        if u.startswith('data:') or u.startswith('javascript:'):
            continue
        if u.startswith('//'):
            u = 'https:' + u
        if not u.startswith('http'):
            try:
                u = urllib.parse.urljoin(base_url, u)
            except Exception:
                continue
        u = u.split(' ')[0].split(',')[0].strip()
        if not u or len(u) > 1024:
            continue
        ul = u.lower()
        if JPG_TOKEN_RE.search(ul) or VIDEO_TOKEN_RE.search(ul) or MJPG_PATH_RE.search(ul):
            urls.append(u)
    # og:image
    for m in re.finditer(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', html, re.I):
        u = m.group(1)
        if u.startswith('//'):
            u = 'https:' + u
        if not u.startswith('http'):
            u = urllib.parse.urljoin(base_url, u)
        urls.append(u)
    # og:video
    for m in re.finditer(r'<meta[^>]+property=["\']og:video["\'][^>]+content=["\']([^"\']+)', html, re.I):
        u = m.group(1)
        if u.startswith('//'):
            u = 'https:' + u
        if not u.startswith('http'):
            u = urllib.parse.urljoin(base_url, u)
        urls.append(u)
    # raw URLs in HTML (last resort)
    for m in re.finditer(r'(?:https?:|//)[^\s"\'<>]+\.(?:jpe?g|png|mjpg|mjpeg|mp4|m3u8)(?:\?[^\s"\'<>]*)?', html, re.I):
        u = m.group(0)
        if u.startswith('//'):
            u = 'https:' + u
        urls.append(u)
    # mjpg in text (e.g. "imageurl=http://x.com/foo.mjpg")
    for m in re.finditer(r'(?:https?:|//)[^\s"\'<>]+/mjpeg[^\s"\'<>]*', html, re.I):
        u = m.group(0)
        if u.startswith('//'):
            u = 'https:' + u
        urls.append(u)
    return list(set(urls))[:8]


def is_paywall(html):
    hl = html.lower()
    return any(t in hl for t in [
        'subscription required', 'sign in to view', 'login to view', 'membership required',
        'please log in to access', 'page not found', 'forbidden', 'cookies must be enabled',
        'access denied', 'abonnement requis', 'requires javascript', 'incapsula',
        'cloudflare', 'just a moment', 'attention required',
    ])


def head_is_image_or_video(s, url):
    try:
        r = s.head(url, timeout=4, allow_redirects=True, verify=False)
        if r.status_code >= 400:
            return False, r.status_code, ''
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


def get_is_image_or_video(s, url):
    """GET with stream=True, peek first bytes."""
    try:
        r = s.get(url, timeout=6, allow_redirects=True, verify=False, stream=True)
        if r.status_code >= 400:
            return None, r.status_code, ''
        ct = r.headers.get('Content-Type', '').lower()
        cl = int(r.headers.get('Content-Length', 0) or 0)
        if 'image/' in ct or 'octet-stream' in ct or 'mpeg' in ct or 'mp4' in ct:
            return url, r.status_code, ct
        if 'text/html' in ct or ct.startswith('text/') or ct == '' or cl > 5000:
            try:
                content = r.raw.read(min(cl, 600_000) if cl and cl > 0 else 200_000, decode_content=True)
                if isinstance(content, bytes):
                    # Check magic bytes for JPEG/PNG
                    if content[:3] == b'\xff\xd8\xff':
                        return url, r.status_code, 'image/jpeg'
                    if content[:8] == b'\x89PNG\r\n\x1a\n':
                        return url, r.status_code, 'image/png'
                    text = content.decode('utf-8', errors='replace')
                    # Tier 1: inline image extractor
                    inner_urls = extract_inline_image_urls(text, url)
                    # Tier 5: iframe/embed/JS/og extractor
                    tier5_urls = tier5_extractor.extract_all(text, url)
                    inner_urls = list(set(inner_urls + tier5_urls))
                    for u in inner_urls:
                        if tier5_extractor.is_stream_url(u):
                            ok, code, ict = head_is_image_or_video(s, u)
                            if ok:
                                return u, code, ict
            except Exception:
                pass
        return None, r.status_code, ct
    except Exception:
        return None, 0, ''


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


def process_chunk(s, chunk_idx, core_data, seen, existing_ids, max_workers=30):
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

    candidates = []
    for i in range(n):
        cam_id = ids[i]
        if not cam_id or cam_id in existing_ids:
            continue
        stream_url = streams[i] if i < len(streams) else ''
        feed_url = feeds[i] if i < len(feeds) else ''
        candidates.append((cam_id, i, stream_url or feed_url))

    def probe(c):
        cam_id, local_idx, url = c
        if not url:
            return None
        if url.lower().strip() in seen:
            return None
        ok, code, ct = head_is_image_or_video(s, url)
        if ok:
            return (cam_id, local_idx, url, ct)
        live_url, gcode, gct = get_is_image_or_video(s, url)
        if live_url:
            return (cam_id, local_idx, live_url, gct)
        return None

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(probe, c) for c in candidates]
        for f in as_completed(futures):
            res = f.result()
            if res is None:
                continue
            cam_id, local_idx, live_url, ct = res
            live_url_lower = live_url.lower().strip()
            if live_url_lower in seen:
                continue
            seen.add(live_url_lower)
            existing_ids.add(cam_id)

            try:
                lat = lats[local_idx] if local_idx < len(lats) else None
                lon = lons[local_idx] if local_idx < len(lons) else None
            except Exception:
                lat = lon = None

            m = re.match(r'(?:https?|rtsp|rtmp)://([^/:]+)', live_url)
            host = m.group(1) if m else ''
            proj_name = host
            if proj_name.startswith('www.'):
                proj_name = proj_name[4:]
            proj_name_short = proj_name.split('.')[0] if '.' in proj_name else proj_name

            ul = live_url.lower()
            if '.m3u8' in ul or '.m3u' in ul:
                kind = 'hls-multipart'
            elif '.mp4' in ul or 'mjpg' in ul or 'mjpeg' in ul:
                kind = 'mjpeg-multipart'
            else:
                kind = 'jpeg-frame'

            try:
                fake_res = {
                    'url': live_url,
                    'family': 'argus-public',
                    'stream_kind': kind,
                    'content_type': ct or 'image/jpeg',
                    'content_length': 0,
                    'weight': 25 if 'mjpg' in ul or 'm3u8' in ul or 'mp4' in ul else 8,
                    'host': host,
                    'port': 443 if live_url.startswith('https') else 80,
                    'ssl': live_url.startswith('https'),
                    'http_status': 200,
                }
                geo = {
                    'country': '', 'regionName': '', 'city': '',
                    'lat': lat or '', 'lon': lon or '',
                    'isp': '', 'org': 'Argus Public Cams', 'as': '',
                    'brand': 'Argus Public Cams',
                    'model': kind if kind else '',
                    '_latlon': (lat, lon),
                }
                entry = csv_writer.entry_from_probe(fake_res, {'source': 'argus-v3'}, geo)
                entry['project_name'] = f'{proj_name_short} webcam (argus)'
                entry['type'] = 'image' if kind == 'jpeg-frame' else 'video'
                entry['live_stream_url'] = live_url
                existing_notes = entry.get('notes', '')
                entry['notes'] = (existing_notes + f'; argus_id={cam_id}').strip('; ')
                csv_writer.append_one(entry)
                added += 1
            except Exception as e:
                log(f'  err cam={cam_id}: {e}')
    return added


def main():
    log('[init] starting Argus v3 ingestion')
    s = session()
    seen = existing_live_urls()
    existing_ids = existing_argus_ids()
    log(f'[init] {len(seen)} existing live URLs, {len(existing_ids)} existing argus IDs')
    core = load_core()
    log(f'[core] {core["count"]} cams in Argus core')
    progress = load_progress()
    done_set = set(progress.get('done_chunks', []))
    start_idx = progress.get('last_idx', -1) + 1
    log(f'[progress] resuming from chunk {start_idx}, {len(done_set)} chunks done previously')

    total_added = 0
    cycle_start = 0
    for chunk_idx in range(start_idx, NUM_CHUNKS):
        if chunk_idx in done_set:
            continue
        try:
            n = process_chunk(s, chunk_idx, core, seen, existing_ids, max_workers=30)
            total_added += n
            done_set.add(chunk_idx)
            progress['done_chunks'] = list(done_set)
            progress['last_idx'] = chunk_idx
            save_progress(progress)
        except Exception as e:
            log(f'  chunk {chunk_idx} err: {e}')
        if (chunk_idx + 1) % 5 == 0:
            log(f'  progress chunk {chunk_idx+1}/{NUM_CHUNKS}, added={total_added}, seen={len(seen)}, existing_ids={len(existing_ids)}')
        # cycle restart: also save after every chunk
        if chunk_idx + 1 >= NUM_CHUNKS:
            log(f'[cycle done] {total_added} new cams. Restarting in 5 min...')
            time.sleep(300)
            progress['last_idx'] = -1  # restart from beginning
            save_progress(progress)
            total_added = 0
    log(f'[done] total added from Argus: {total_added}')


if __name__ == '__main__':
    main()
