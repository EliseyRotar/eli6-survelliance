"""Caltrans CCTV ingestor — pulls live traffic cameras from all 12 Caltrans districts.

Each district returns ~750 cams with HLS streams + JPEG snapshots + lat/lon.
Total: ~9,000 cams.
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
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\caltrans_log.txt'

DISTRICTS = list(range(1, 13))
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0'


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
    s.headers.update({'User-Agent': UA, 'Accept': 'application/json'})
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


def existing_caltrans_ids():
    ids = set()
    if not os.path.exists(CSV_PATH):
        return ids
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        rows = list(csv.reader(f))
    for row in rows[1:]:
        if len(row) > 33 and row[33]:
            for m in re.finditer(r'caltrans_id=([^\s;,]+)', row[33]):
                ids.add(m.group(1))
    return ids


def fetch_district(s, district):
    url = f'https://cwwp2.dot.ca.gov/data/d{district:02d}/cctv/cctvStatusD{district:02d}.json'
    try:
        r = s.get(url, timeout=30)
        if r.status_code == 200:
            return r.json().get('data', [])
    except Exception as e:
        log(f'  D{district:02d} err: {e}')
    return []


def add_cam(rec, seen, existing_ids, total_added):
    raw_cam_id = rec.get('cctv', {}).get('index', '')
    district = rec.get('cctv', {}).get('location', {}).get('district', '')
    # Make ID globally unique by prefixing district
    cam_id = f'D{district}-{raw_cam_id}' if district else raw_cam_id
    if not raw_cam_id or cam_id in existing_ids:
        return False
    img = rec.get('cctv', {}).get('imageData', {})
    static = img.get('static', {})
    hls = img.get('streamingVideoURL', '')
    jpg = static.get('currentImageURL', '')
    live_url = hls or jpg
    if not live_url:
        return False
    lu = live_url.lower().strip()
    if lu in seen:
        existing_ids.add(cam_id)
        return False

    loc = rec.get('cctv', {}).get('location', {})
    name = loc.get('locationName', 'Caltrans cam')
    city = loc.get('nearbyPlace', '')
    county = loc.get('county', '')
    route = loc.get('route', '')
    direction = loc.get('direction', '')
    state = 'California'
    country = 'US'

    m = re.match(r'(?:https?|rtsp|rtmp)://([^/:]+)', live_url)
    host = m.group(1) if m else ''
    proj_name_short = name.split(' -- ')[0] if ' -- ' in name else name
    proj_name_short = re.sub(r'[^\w\-]', '_', proj_name_short)[:40] or 'caltrans'

    if '.m3u8' in lu or '.m3u' in lu:
        kind = 'hls-multipart'
    elif '.mp4' in lu or 'mjpg' in lu or 'mjpeg' in lu:
        kind = 'mjpeg-multipart'
    else:
        kind = 'jpeg-frame'

    fake_res = {
        'url': live_url,
        'family': f'caltrans-d{rec["cctv"]["location"]["district"]}',
        'stream_kind': kind,
        'content_type': 'application/vnd.apple.mpegurl' if 'm3u8' in lu else 'image/jpeg',
        'content_length': 0,
        'weight': 30 if 'm3u8' in lu else 10,
        'host': host,
        'port': 443 if live_url.startswith('https') else 80,
        'ssl': live_url.startswith('https'),
        'http_status': 200,
    }
    geo = {
        'country': country,
        'regionName': state,
        'city': city,
        'lat': loc.get('latitude', ''),
        'lon': loc.get('longitude', ''),
        'isp': '',
        'org': 'Caltrans (California DOT)',
        'as': '',
        '_latlon': (loc.get('latitude', ''), loc.get('longitude', '')),
    }
    try:
        entry = csv_writer.entry_from_probe(fake_res, {'source': 'caltrans'}, geo)
        entry['project_name'] = f'{proj_name_short} cam'
        entry['type'] = 'image' if kind == 'jpeg-frame' else 'video'
        entry['live_stream_url'] = live_url
        existing_notes = entry.get('notes', '')
        entry['notes'] = (existing_notes + f'; caltrans_id={cam_id}; county={county}; route={route}; dir={direction}').strip('; ')
        entry['likely_subject'] = f'Highway {route} {direction} ({city}, {county} County)'
        idx = csv_writer.append_one(entry)
        if idx:
            seen.add(lu)
            existing_ids.add(cam_id)
            total_added[0] += 1
            return True
    except Exception as e:
        log(f'  err cam={cam_id}: {e}')
    return False


def main():
    log('[init] starting Caltrans ingestion')
    s = session()
    seen = existing_live_urls()
    existing_ids = existing_caltrans_ids()
    log(f'[init] {len(seen)} existing live URLs, {len(existing_ids)} existing caltrans IDs')

    total_added_ref = [0]
    while True:
        for d in DISTRICTS:
            log(f'[D{d:02d}] fetching...')
            cams = fetch_district(s, d)
            log(f'[D{d:02d}] {len(cams)} cams')
            for cam in cams:
                add_cam(cam, seen, existing_ids, total_added_ref)
        log(f'[cycle done] added={total_added_ref[0]} cams. Re-running in 30 min...')
        # Refresh existing_ids in case other ingestors added more
        existing_ids = existing_caltrans_ids()
        seen = existing_live_urls()
        total_added_ref[0] = 0
        time.sleep(1800)


if __name__ == '__main__':
    main()
