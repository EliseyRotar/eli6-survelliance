"""Live-Environment-Streams ingestion.

Reads willytop8/Live-Environment-Streams/streams.geojson (5997 streams,
98 countries, ~4226 active) and adds the HLS / direct-video ones to our
controllable_Webcams.csv.

Source: https://github.com/willytop8/Live-Environment-Streams
"""

import csv
import json
import os
import sys
import time
import urllib.parse
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')
import probe_lib
import csv_writer

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\live_env_log.txt'
DATA_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\live_env_streams.geojson'


def session():
    s = requests.Session()
    retries = Retry(total=0)
    s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=40, pool_maxsize=40))
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=40, pool_maxsize=40))
    s.headers.update({'User-Agent': 'Mozilla/5.0'})
    return s


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


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


import re


def main():
    s = session()
    seen = existing_hosts()
    log(f'[init] {len(seen)} existing hosts')

    if not os.path.exists(DATA_PATH):
        log('[err] run live_env_downloader.py first')
        return

    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    feats = data.get('features', [])
    log(f'[load] {len(feats)} streams from willytop8/Live-Environment-Streams')

    # Filter to active + direct (hls or direct mjpg/mp4 we can play)
    candidates = []
    skipped_html = 0
    for feat in feats:
        p = feat.get('properties', {})
        url = p.get('url', '')
        url_type = p.get('url_type', '')
        status = p.get('status', '')
        country = p.get('country_code', '')
        scene = p.get('scene_type', '')
        env = p.get('environment', '')
        coords = feat.get('geometry', {}).get('coordinates', [None, None])

        if not url:
            continue
        if status != 'active':
            continue
        if 'youtube.com' in url or 'youtu.be' in url:
            continue  # skip YouTube
        if url_type in ('html_page',):
            skipped_html += 1
            continue  # skip SkylineWebcams HTML wrapper pages
        # Skip if hostname already in CSV
        m = re.match(r'https?://([^/]+)', url)
        if not m:
            continue
        h = m.group(1).lower()
        if h in seen:
            continue
        candidates.append({
            'url': url,
            'host': h,
            'country': country,
            'city': p.get('name', ''),
            'scene': scene,
            'env': env,
            'lat': coords[1] if len(coords) > 1 else '',
            'lon': coords[0] if len(coords) > 0 else '',
            'resolution': p.get('resolution', '') or '',
            'source_family': p.get('source_family', '') or '',
            'url_type': url_type,
            'last_verified': p.get('last_verified', '') or '',
            'display_name': p.get('display_name', '') or '',
        })
    log(f'[cands] {len(candidates)} candidates (skipped {skipped_html} html_page)')

    added = 0
    skipped_dup = 0
    for c in candidates:
        h = c['host']
        if h in seen:
            skipped_dup += 1
            continue
        seen.add(h)
        # Build entry from HLS URL
        try:
            m = re.match(r'https?://([^/]+)/?(\S*)', c['url'])
            host_port = m.group(1)
            path = m.group(2)
            hh = host_port.split(':')
            host = hh[0]
            port = int(hh[1]) if len(hh) > 1 else (443 if c['url'].startswith('https') else 80)
        except Exception:
            continue

        # HLS = playlist M3U8 — type tag as 'live-stream'
        probe_res = {
            'url': c['url'],
            'family': 'hls-live-stream',
            'stream_kind': 'hls-live',
            'content_type': 'application/vnd.apple.mpegurl',
            'content_length': 0,
            'weight': 50,
            'host': host,
            'port': port,
            'ssl': c['url'].startswith('https'),
            'http_status': 200,
        }
        geo = {
            'country': c['country'],
            'regionName': '',
            'city': c['city'],
            'lat': c['lat'],
            'lon': c['lon'],
            'isp': '',
            'org': c['source_family'],
            'as': '',
        }
        try:
            entry = csv_writer.entry_from_probe(probe_res, {'source': 'live_env'}, geo)
        except Exception:
            continue
        try:
            idx = csv_writer.append_one(entry)
            added += 1
            if added % 25 == 0:
                log(f'  ADDED #{added} ({c["display_name"]} / {c["country"]})')
        except Exception as e:
            log(f'  err: {e}')

    log(f'[done] added {added}, skipped {skipped_dup} dup, dedup-csv-host={len(seen)}')


if __name__ == '__main__':
    main()
