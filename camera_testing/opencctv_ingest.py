"""OpenCCTV ingestion — pull real source feed URLs from opencctv.org's catalog.

Endpoints (no key needed):
- GET https://opencctv.org/api/cameras/markers  -> {count, ids, lats, lngs, cats, fts, geo, geoSets}
- POST https://opencctv.org/api/cameras/batch {ids:[<=50]} -> array of full records with feed_url

Strategy:
1. Fetch markers once (158k+ ids with lat/lng parallel arrays).
2. Spawn parallel workers (5) each pulling batches of 50 IDs.
3. For each record, if feed_url exists and not already in CSV, add to CSV.
4. Use force_direct=1 to prefer direct image/video URLs over proxy_zone.

Run as background; persist progress to disk.
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
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\opencctv_log.txt'
PROGRESS_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\opencctv_progress.json'
MARKERS_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\opencctv_markers.json'

API_MARKERS = 'https://opencctv.org/api/cameras/markers'
API_BATCH = 'https://opencctv.org/api/cameras/batch'
BATCH_SIZE = 50
MAX_WORKERS = 6
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'


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
    s.headers.update({
        'User-Agent': UA,
        'Accept': 'application/json, text/plain, */*',
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


def existing_opencctv_ids():
    ids = set()
    if not os.path.exists(CSV_PATH):
        return ids
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        rows = list(csv.reader(f))
    for row in rows[1:]:
        if len(row) > 33 and row[33]:
            for m in re.finditer(r'opencctv_id=([^\s;,]+)', row[33]):
                ids.add(m.group(1))
    return ids


def load_progress():
    if os.path.exists(PROGRESS_PATH):
        try:
            with open(PROGRESS_PATH, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {'next_batch_idx': 0, 'total_processed': 0, 'total_added': 0}


def save_progress(p):
    try:
        with open(PROGRESS_PATH, 'w') as f:
            json.dump(p, f)
    except Exception:
        pass


def fetch_markers(s):
    if os.path.exists(MARKERS_PATH):
        log(f'[markers] using cached {MARKERS_PATH}')
        with open(MARKERS_PATH, 'r') as f:
            return json.load(f)
    log(f'[markers] GET {API_MARKERS}')
    r = s.get(API_MARKERS, timeout=60)
    r.raise_for_status()
    data = r.json()
    with open(MARKERS_PATH, 'w') as f:
        json.dump(data, f)
    return data


def post_batch(s, ids, retries=4):
    for i in range(retries):
        try:
            r = s.post(API_BATCH, json={'ids': ids}, timeout=30, headers={'Content-Type': 'application/json'})
            if r.status_code == 429:
                time.sleep(8 + 4 * i)
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if i == retries - 1:
                return None
            time.sleep(2 + 2 * i)
    return None


def add_cam(rec, seen, existing_ids, total_added):
    cam_id = rec.get('id', '')
    if not cam_id or cam_id in existing_ids:
        return False
    feed_url = rec.get('feed_url', '')
    if not feed_url:
        return False
    fu = feed_url.lower().strip()
    if fu in seen:
        existing_ids.add(cam_id)
        return False

    ft = (rec.get('feed_type') or 'image').lower()
    # Skip iframe (not playable in browser)
    if ft == 'iframe':
        existing_ids.add(cam_id)
        return False

    m = re.match(r'(?:https?|rtsp|rtmp)://([^/:]+)', feed_url)
    host = m.group(1) if m else ''
    proj_name = host
    if proj_name.startswith('www.'):
        proj_name = proj_name[4:]
    proj_name_short = proj_name.split('.')[0] if '.' in proj_name else proj_name

    if 'm3u8' in fu or 'm3u' in fu:
        kind = 'hls-multipart'
    elif 'mp4' in fu or 'mjpeg' in fu or 'mjpg' in fu:
        kind = 'mjpeg-multipart'
    else:
        kind = 'jpeg-frame'

    port = 443 if feed_url.startswith('https') else 80

    country_iso = rec.get('country', '') or ''
    state = rec.get('state', '') or ''
    city = rec.get('city', '') or ''
    name = rec.get('name', '') or proj_name_short
    cat = rec.get('category', '') or 'public'
    src = rec.get('source', '') or 'opencctv'

    fake_res = {
        'url': feed_url,
        'family': f'opencctv-{src}',
        'stream_kind': kind,
        'content_type': 'image/jpeg',
        'content_length': 0,
        'weight': 25 if 'mjpg' in fu or 'm3u8' in fu or 'mp4' in fu else 8,
        'host': host,
        'port': port,
        'ssl': feed_url.startswith('https'),
        'http_status': 200,
    }
    geo = {
        'country': country_iso,
        'regionName': state,
        'city': city,
        'lat': rec.get('lat', '') or '',
        'lon': rec.get('lng', '') or '',
        'isp': '',
        'org': f'OpenCCTV ({src})',
        'as': '',
        '_latlon': (rec.get('lat', ''), rec.get('lng', '')),
    }
    try:
        entry = csv_writer.entry_from_probe(fake_res, {'source': 'opencctv'}, geo)
        entry['project_name'] = f'{name[:80]} webcam'
        entry['type'] = 'image' if kind == 'jpeg-frame' else 'video'
        entry['live_stream_url'] = feed_url
        existing_notes = entry.get('notes', '')
        entry['notes'] = (existing_notes + f'; opencctv_id={cam_id}; cat={cat}').strip('; ')
        entry['category'] = cat
        idx = csv_writer.append_one(entry)
        if idx:
            seen.add(fu)
            existing_ids.add(cam_id)
            total_added[0] += 1
            return True
    except Exception as e:
        log(f'  err cam={cam_id}: {e}')
    return False


def main():
    log('[init] starting OpenCCTV ingestion')
    s = session()
    seen = existing_live_urls()
    existing_ids = existing_opencctv_ids()
    log(f'[init] {len(seen)} existing live URLs, {len(existing_ids)} existing opencctv IDs')

    data = fetch_markers(s)
    ids_all = data.get('ids', [])
    log(f'[markers] {len(ids_all)} total cams')

    progress = load_progress()
    start_batch = progress.get('next_batch_idx', 0)
    total_added_ref = [progress.get('total_added', 0)]
    total_processed_ref = [progress.get('total_processed', 0)]

    chunks = [ids_all[i:i + BATCH_SIZE] for i in range(0, len(ids_all), BATCH_SIZE)]
    log(f'[chunks] {len(chunks)} batches of {BATCH_SIZE}')

    cycle_count = 0
    while True:
        for batch_idx in range(start_batch, len(chunks)):
            ids = chunks[batch_idx]
            records = post_batch(s, ids)
            if not records:
                progress['next_batch_idx'] = batch_idx + 1
                save_progress(progress)
                continue
            for rec in records:
                add_cam(rec, seen, existing_ids, total_added_ref)
            total_processed_ref[0] += len(ids)
            progress['next_batch_idx'] = batch_idx + 1
            progress['total_added'] = total_added_ref[0]
            progress['total_processed'] = total_processed_ref[0]
            if (batch_idx + 1) % 20 == 0:
                save_progress(progress)
                log(f'  progress batch {batch_idx+1}/{len(chunks)}, added={total_added_ref[0]}, processed={total_processed_ref[0]}')
        # Cycle complete
        cycle_count += 1
        log(f'[cycle {cycle_count}] done. Restarting from beginning in 30 min...')
        progress['next_batch_idx'] = 0
        save_progress(progress)
        # Re-load existing IDs (since we may have new ones from other ingestors)
        existing_ids = existing_opencctv_ids()
        seen = existing_live_urls()
        total_added_ref[0] = 0
        time.sleep(1800)  # 30 min cooldown


if __name__ == '__main__':
    main()
