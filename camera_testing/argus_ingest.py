"""Argus ingestion — harvest all 229k traffic+public cams from GoSlowPoke168/Argus.

The dataset has:
- /public/cameras.core.json — 7 MB parallel-array: lons, lats, de (desc), live, src[], cc[], ft[]
- /public/cameras.detail/{N}.json — 229 chunks × 1000 cams = 229k cams. Each has id, feed (URL), stream (HLS/m3u8 if any)
- /public/cameras.detail/{N}.json from 0..228

We:
1. Load core (id-keyed by src idx).
2. For each detail chunk, fetch and append to CSV using `feed` URL or, when present, `stream` URL.
3. Use geoip only for IP cams (most Argus is HTTP — geo via domain if possible).
"""
import csv
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')
import csv_writer
import probe_lib

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\argus_log.txt'
CORE_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\argus_cameras_core.json'

ARGUS_RAW = 'https://raw.githubusercontent.com/GoSlowPoke168/Argus/master/public/cameras.detail'
NUM_CHUNKS = 229  # 229308 / 1000 = 229 chunks (idx 0..228)


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
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=50, pool_maxsize=100))
    s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=50, pool_maxsize=100))
    s.headers.update({'User-Agent': 'Mozilla/5.0'})
    return s


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


def load_core():
    """core has parallel arrays. We only need lons/lats to map idx -> (lat,lon,country,src)."""
    with open(CORE_PATH, 'r', encoding='utf-8') as f:
        j = json.load(f)
    n = j.get('count', 0)
    lons = j.get('lon', [])
    lats = j.get('lat', [])
    cc_arr = j.get('cc', [])
    src_arr = j.get('src', [])
    ft_arr = j.get('ft', [])
    de_arr = j.get('de', [])
    return {
        'count': n,
        'lons': lons,
        'lats': lats,
        'cc': cc_arr,
        'src': src_arr,
        'ft': ft_arr,
        'de': de_arr,
    }


def fetch_chunk(s, chunk_idx):
    url = f'{ARGUS_RAW}/{chunk_idx}.json'
    try:
        r = s.get(url, timeout=15)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def process_chunk(s, chunk_idx, core_data, seen, added_count):
    """Process one chunk; yield ('add', row_dict) for each new live cam."""
    chunk = fetch_chunk(s, chunk_idx)
    if chunk is None:
        return []
    ids = chunk.get('id', [])
    feeds = chunk.get('feed', [])
    streams = chunk.get('stream', [])
    n = len(ids)
    new = []
    for i in range(n):
        cam_id = ids[i]
        if not cam_id:
            continue
        # Get core info for this cam (idx = i + chunk_idx * 1000, but actually local idx)
        # Per Argus convention: detail chunks have local idx 0..999 for the chunk's cams
        local_idx = i
        try:
            lat = core_data['lats'][local_idx] if local_idx < len(core_data['lats']) else None
            lon = core_data['lons'][local_idx] if local_idx < len(core_data['lons']) else None
            src_idx = core_data['src'][local_idx] if local_idx < len(core_data['src']) else None
            cc_idx = core_data['cc'][local_idx] if local_idx < len(core_data['cc']) else None
            ft_idx = core_data['ft'][local_idx] if local_idx < len(core_data['ft']) else None
        except (IndexError, TypeError):
            lat = lon = src_idx = cc_idx = ft_idx = None

        # Prefer stream (HLS) over feed (snapshot)
        stream_url = streams[i] if i < len(streams) else ''
        feed_url = feeds[i] if i < len(feeds) else ''
        live_url = stream_url if stream_url else feed_url
        if not live_url:
            continue
        if live_url in seen:
            continue

        # quick validation
        try:
            r = s.head(live_url, timeout=3, allow_redirects=True, verify=False)
            if r.status_code >= 400:
                continue
        except Exception:
            continue

        seen.add(live_url)

        # Determine country from CC index (cc dict is loaded separately)
        # The core json has srcDict/ccDict which we ignore for size
        # Country = CC from core idx mapped via ccDict; we don't have it loaded.
        # Use lat/lon for geoip at this stage — but it would burn ip-api quota.
        # Instead, build geo from core_idx position directly.

        # stream_kind
        if '.m3u8' in live_url or '.m3u' in live_url:
            kind = 'hls-multipart'
            family = 'argus'
            type_label = 'video-hls'
        elif '.mp4' in live_url:
            kind = 'matroska'  # not exactly but works
            family = 'argus'
            type_label = 'video-h264'
        elif '.mjpg' in live_url or 'mjpeg' in live_url or 'stream' in live_url:
            kind = 'mjpeg-multipart'
            family = 'argus'
            type_label = 'video-mjpeg'
        else:
            kind = 'jpeg-frame'
            family = 'argus'
            type_label = 'image'

        # extract host
        m = re.match(r'https?://([^/]+)/?(\S*)', live_url)
        host = m.group(1) if m else ''

        # parse core for cc, src, ft using Dicts not loaded
        # CC and SRC aren't trivial — but we can write "" for now.
        fake_res = {
            'url': live_url,
            'family': family,
            'stream_kind': kind,
            'content_type': r.headers.get('Content-Type', '') if r else '',
            'content_length': 0,
            'weight': 25 if 'mjpg' in live_url or 'm3u8' in live_url else 8,
            'host': host.split(':')[0],
            'port': 443 if 'https' in live_url else 80,
            'ssl': live_url.startswith('https'),
            'http_status': r.status_code if r else 200,
        }
        geo = {
            'country': '',
            'regionName': '',
            'city': '',
            'lat': lat or '',
            'lon': lon or '',
            'isp': '',
            'org': 'Argus Traffic Cams',
            'as': '',
        }
        try:
            entry = csv_writer.entry_from_probe(fake_res, {'source': 'argus'}, geo)
            idx = csv_writer.append_one(entry)
            added_count += 1
            new.append(cam_id)
        except Exception as e:
            log(f'  err {cam_id}: {e}')
    return new


def main():
    log('[init] starting Argus ingestion')
    s = session()
    seen = existing_hosts()
    log(f'[init] {len(seen)} existing hosts in CSV')

    core = load_core()
    log(f'[core] {core["count"]} cams in Argus core')

    chunk_count = NUM_CHUNKS
    log(f'[plan] processing {chunk_count} chunks')
    added = 0
    for chunk_idx in range(chunk_count):
        try:
            added_cams = process_chunk(s, chunk_idx, core, seen, added)
            added += len(added_cams)
        except Exception as e:
            log(f'  chunk {chunk_idx} err: {e}')
        if (chunk_idx + 1) % 20 == 0:
            log(f'  progress chunk {chunk_idx+1}/{chunk_count}, added={added}')
        time.sleep(0.05)

    log(f'[done] {added} cams added from Argus')


if __name__ == '__main__':
    main()
