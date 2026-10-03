"""TfL JamCam ingestor - pulls 890 London traffic cams.

API: GET https://api.tfl.gov.uk/Place/Type/JamCam (no key needed)
Each cam has imageUrl (.jpg), videoUrl (.mp4), lat, lon.
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
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tfl_log.txt'

API = 'https://api.tfl.gov.uk/Place/Type/JamCam'
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
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=30, pool_maxsize=60))
    s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=30, pool_maxsize=60))
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


def existing_tfl_ids():
    ids = set()
    if not os.path.exists(CSV_PATH):
        return ids
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        rows = list(csv.reader(f))
    for row in rows[1:]:
        if len(row) > 33 and row[33]:
            for m in re.finditer(r'tfl_id=([^\s;,]+)', row[33]):
                ids.add(m.group(1))
    return ids


def fetch_all(s):
    try:
        r = s.get(API, timeout=30)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        log(f'  fetch err: {e}')
    return []


def add_cam(rec, seen, existing_ids, total_added):
    cam_id = rec.get('id', '')
    if not cam_id or cam_id in existing_ids:
        return False
    img_url = ''
    vid_url = ''
    for ap in rec.get('additionalProperties', []):
        if ap.get('key') == 'imageUrl':
            img_url = ap.get('value', '')
        elif ap.get('key') == 'videoUrl':
            vid_url = ap.get('value', '')
    live_url = vid_url or img_url
    if not live_url:
        return False
    lu = live_url.lower().strip()
    if lu in seen:
        existing_ids.add(cam_id)
        return False

    name = rec.get('commonName', 'Tfl cam')
    lat = rec.get('lat', '')
    lon = rec.get('lon', '')

    m = re.match(r'(?:https?|rtsp|rtmp)://([^/:]+)', live_url)
    host = m.group(1) if m else ''
    proj_name_short = re.sub(r'[^\w\-]', '_', name)[:40] or 'tfl'

    if '.mp4' in lu:
        kind = 'mjpeg-multipart'
    elif '.jpg' in lu or '.jpeg' in lu:
        kind = 'jpeg-frame'
    else:
        kind = 'jpeg-frame'

    fake_res = {
        'url': live_url,
        'family': 'tfl-jamcam',
        'stream_kind': kind,
        'content_type': 'video/mp4' if '.mp4' in lu else 'image/jpeg',
        'content_length': 0,
        'weight': 28 if '.mp4' in lu else 10,
        'host': host,
        'port': 443 if live_url.startswith('https') else 80,
        'ssl': live_url.startswith('https'),
        'http_status': 200,
    }
    geo = {
        'country': 'United Kingdom',
        'regionName': 'Greater London',
        'city': 'London',
        'lat': lat,
        'lon': lon,
        'isp': '',
        'org': 'Transport for London',
        'as': '',
        '_latlon': (lat, lon),
    }
    try:
        entry = csv_writer.entry_from_probe(fake_res, {'source': 'tfl-jamcam'}, geo)
        entry['project_name'] = f'{proj_name_short} (Tfl)'
        entry['type'] = 'video' if '.mp4' in lu else 'image'
        entry['live_stream_url'] = live_url
        existing_notes = entry.get('notes', '')
        entry['notes'] = (existing_notes + f'; tfl_id={cam_id}').strip('; ')
        entry['likely_subject'] = 'London traffic / road junction'
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
    log('[init] starting TfL JamCam ingestion')
    s = session()
    seen = existing_live_urls()
    existing_ids = existing_tfl_ids()
    log(f'[init] {len(seen)} existing live URLs, {len(existing_ids)} existing tfl IDs')

    total_added_ref = [0]
    while True:
        cams = fetch_all(s)
        log(f'[fetch] {len(cams)} cams from TfL')
        for cam in cams:
            add_cam(cam, seen, existing_ids, total_added_ref)
        log(f'[cycle done] added={total_added_ref[0]} cams. Re-running in 6 hours...')
        existing_ids = existing_tfl_ids()
        seen = existing_live_urls()
        total_added_ref[0] = 0
        time.sleep(21600)  # 6 hours


if __name__ == '__main__':
    main()
