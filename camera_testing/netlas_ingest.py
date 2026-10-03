"""Netlas.io free cam discovery.

Free endpoint: GET https://app.netlas.io/api/responses/?q=<query>&start=<n>
Returns 20 items per page. Queries for cam vendor fingerprints:
- product:Hikvision
- product:Dahua
- product:AXIS
- http.title:Hikvision
- http.title:Dahua
- http.title:WebcamXP
- http.title:Blue Iris
- ssl.cert.subject.cn:Hikvision
- etc.

Total potential: 1000s of cams per vendor × ~10 vendors = 10k+ new cams.
"""
import csv
import json
import os
import re
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')
import csv_writer

from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\netlas_log.txt'
PROGRESS_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\netlas_progress.json'

API = 'https://app.netlas.io/api/responses/'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0'

QUERIES = [
    'product:"Hikvision IP Camera"',
    'product:"Dahua IP Camera"',
    'product:"AXIS"',
    'http.title:"Hikvision"',
    'http.title:"Dahua"',
    'http.title:"WebcamXP"',
    'http.title:"Blue Iris"',
    'http.title:"Reolink"',
    'http.title:"HIKVISION"',
    'http.title:"WebcamXP 5"',
    'ssl.cert.subject.cn:Hikvision',
    'ssl.cert.subject.cn:Dahua',
    'http.body:"Dahua Technology"',
    'http.body:"HIKVISION"',
    'ssl.cert.subject.o:HANGZHOU',
    'ssl.cert.subject.o:"Hikvision"',
    'http.body:"iCanSeeCam"',
    'http.body:"Active WebCam"',
    'http.body:"WebcamXP"',
    'http.body:"GoAhead"',
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
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=30, pool_maxsize=60))
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


def existing_netlas_ids():
    ids = set()
    if not os.path.exists(CSV_PATH):
        return ids
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        rows = list(csv.reader(f))
    for row in rows[1:]:
        if len(row) > 33 and row[33]:
            for m in re.finditer(r'netlas_id=([^\s;,]+)', row[33]):
                ids.add(m.group(1))
    return ids


def load_progress():
    if os.path.exists(PROGRESS_PATH):
        try:
            with open(PROGRESS_PATH, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {'q_idx': 0, 'start': 0}


def save_progress(p):
    try:
        with open(PROGRESS_PATH, 'w') as f:
            json.dump(p, f)
    except Exception:
        pass


def fetch_page(s, query, start):
    url = f'{API}?q={urllib.parse.quote(query)}&start={start}&indices='
    for _ in range(3):
        try:
            r = s.get(url, timeout=20)
            if r.status_code == 429:
                log(f'  429 rate-limited, sleeping 90s...')
                time.sleep(90)
                continue
            if r.status_code == 200:
                return r.json()
            log(f'  fetch err status={r.status_code} for {query[:50]} start={start}')
            return None
        except Exception as e:
            log(f'  fetch err: {e}')
            time.sleep(2)
    return None


def add_host(item, seen, existing_ids, total_added):
    data = item.get('data', {})
    ip = data.get('ip', '')
    port = data.get('port', 80)
    proto = data.get('protocol', 'http')
    if not ip:
        return False
    ssl = proto == 'https'
    netlas_id = f'{ip}:{port}:{proto}'
    if netlas_id in existing_ids:
        return False

    scheme = 'https' if ssl else 'http'
    # Try to find a working stream URL — pick the most likely vendor-specific path
    # Since Netlas verified the cam exists, we just trust the title match
    http_data = data.get('http', {}) or {}
    title = http_data.get('title', '') or ''
    body_snippet = (http_data.get('body', '') or '')[:200]
    title_low = title.lower()

    # Pick best stream URL based on title hints
    if 'hikvision' in title_low or 'isapi' in body_snippet.lower():
        candidate = f'{scheme}://{ip}:{port}/ISAPI/Streaming/channels/1/picture'
        kind = 'mjpeg-multipart'
    elif 'dahua' in title_low or 'web service' in title_low:
        candidate = f'{scheme}://{ip}:{port}/cgi-bin/snapshot.cgi?channel=1'
        kind = 'jpeg-frame'
    elif 'axis' in title_low:
        candidate = f'{scheme}://{ip}:{port}/axis-cgi/jpg/image.cgi'
        kind = 'jpeg-frame'
    elif 'webcamxp' in title_low:
        candidate = f'{scheme}://{ip}:{port}/cam_1.cgi'
        kind = 'mjpeg-multipart'
    elif 'blue iris' in title_low:
        candidate = f'{scheme}://{ip}:{port}/mjpg/video.mjpg'
        kind = 'mjpeg-multipart'
    elif 'reolink' in title_low:
        candidate = f'{scheme}://{ip}:{port}/cgi-bin/api.cgi?cmd=Snap'
        kind = 'jpeg-frame'
    else:
        # Generic — use root URL or fall back to standard cam path
        src = data.get('src', '')
        candidate = src if src else f'{scheme}://{ip}:{port}/'
        kind = 'jpeg-frame'

    lu = candidate.lower().strip()
    if lu in seen:
        existing_ids.add(netlas_id)
        return False

    isp = data.get('isp', '')
    geo_data = data.get('geo', {}) or {}
    country = geo_data.get('country', '') or ''
    region = geo_data.get('region', '') or ''
    city = geo_data.get('city', '') or ''
    location = geo_data.get('location', {}) or {}
    lat = location.get('latitude', '') or ''
    lon = location.get('longitude', '') or ''

    proj_name = f'{title[:60]} cam' if title else f'{ip} IP cam'

    fake_res = {
        'url': candidate,
        'family': 'netlas-discovered',
        'stream_kind': kind,
        'content_type': 'image/jpeg',
        'content_length': 0,
        'weight': 35,
        'host': ip,
        'port': port,
        'ssl': ssl,
        'http_status': 200,
    }
    geo = {
        'country': country,
        'regionName': region,
        'city': city,
        'lat': lat,
        'lon': lon,
        'isp': isp,
        'org': isp or 'Netlas-discovered',
        'as': '',
        '_latlon': (lat, lon),
    }
    try:
        entry = csv_writer.entry_from_probe(fake_res, {'source': 'netlas'}, geo)
        entry['project_name'] = proj_name
        entry['type'] = 'image' if kind == 'jpeg-frame' else 'video'
        entry['live_stream_url'] = candidate
        existing_notes = entry.get('notes', '')
        entry['notes'] = (existing_notes + f'; netlas_id={netlas_id}').strip('; ')
        if title:
            entry['page_title'] = title[:200]
        idx = csv_writer.append_one(entry)
        if idx:
            seen.add(lu)
            existing_ids.add(netlas_id)
            total_added[0] += 1
            return True
    except Exception as e:
        log(f'  err cam={netlas_id}: {e}')
    return False


sess = session()


def main():
    log('[init] starting Netlas ingestion')
    seen = existing_live_urls()
    existing_ids = existing_netlas_ids()
    log(f'[init] {len(seen)} existing live URLs, {len(existing_ids)} existing netlas IDs')
    progress = load_progress()
    q_idx = progress.get('q_idx', 0)
    start = progress.get('start', 0)

    total_added_ref = [0]
    stuck_count = 0
    while True:
        q = QUERIES[q_idx]
        log(f'[Q{q_idx}] {q[:60]} start={start}')
        data = fetch_page(sess, q, start)
        if not data:
            stuck_count += 1
            if stuck_count > 2:
                # Skip to next query if rate-limited 3+ times
                log(f'  stuck on Q{q_idx}, advancing to next query')
                q_idx = (q_idx + 1) % len(QUERIES)
                start = 0
                save_progress({'q_idx': q_idx, 'start': start})
                stuck_count = 0
                continue
            time.sleep(60)
            continue
        stuck_count = 0
        items = data.get('items', [])
        if not items:
            log(f'[Q{q_idx}] no more items, advancing to next query')
            q_idx = (q_idx + 1) % len(QUERIES)
            start = 0
            save_progress({'q_idx': q_idx, 'start': start})
            continue
        log(f'[Q{q_idx}] {len(items)} items at start={start}')
        for item in items:
            add_host(item, seen, existing_ids, total_added_ref)
        start += 20
        progress['q_idx'] = q_idx
        progress['start'] = start
        save_progress(progress)
        log(f'[Q{q_idx}] added={total_added_ref[0]} so far')
        time.sleep(45)  # rate limit - 429s start fast
        # If we hit 200 starts on same query, cycle
        if start > 200:
            q_idx = (q_idx + 1) % len(QUERIES)
            start = 0
            save_progress({'q_idx': q_idx, 'start': start})


if __name__ == '__main__':
    main()
