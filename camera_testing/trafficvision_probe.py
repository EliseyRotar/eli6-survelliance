"""Probe all 845 TV source IDs and save only the live ones."""
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

SOURCES_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\trafficvision_sources.txt'
LIVE_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\trafficvision_live.txt'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\trafficvision_probe_log.txt'

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0'


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG_PATH, 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass


def session():
    s = requests.Session()
    retries = Retry(total=0)
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=100, pool_maxsize=200))
    s.headers.update({'User-Agent': UA, 'Accept': 'application/json'})
    return s


def load_sources():
    with open(SOURCES_PATH) as f:
        return [line.strip() for line in f if line.strip()]


def probe_one(s, source_id):
    url = f'https://data.trafficvision.live/camera-data/{source_id}-cameras.json'
    try:
        r = s.get(url, timeout=12)
        if r.status_code == 200:
            try:
                d = r.json()
                cams = d.get('cameras', [])
                meta = d.get('_metadata', {})
                cam_count = meta.get('cameraCount', len(cams))
                return (source_id, True, cam_count, meta)
            except Exception:
                return (source_id, False, 0, 'parse_err')
        return (source_id, False, 0, f'status_{r.status_code}')
    except Exception as e:
        return (source_id, False, 0, str(e)[:40])


def main():
    log('[init] probing all TV source IDs')
    s = session()
    sources = load_sources()
    log(f'[init] {len(sources)} sources to probe')

    live_sources = []
    done = 0
    last_log = time.time()
    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(probe_one, s, src): src for src in sources}
        for fut in as_completed(futures):
            try:
                src, ok, count, meta = fut.result()
            except Exception:
                continue
            done += 1
            if ok:
                live_sources.append((src, count, meta))
                log(f'  LIVE: {src} ({count} cams)')
            if time.time() - last_log > 5:
                log(f'  progress: {done}/{len(sources)}')
                last_log = time.time()
    # Save live sources sorted by count desc
    live_sources.sort(key=lambda x: -x[1])
    with open(LIVE_PATH, 'w') as f:
        for src, count, _ in live_sources:
            f.write(f'{src}\t{count}\n')
    total = sum(c for _, c, _ in live_sources)
    log(f'[done] {len(live_sources)} live sources, total {total} cams')


if __name__ == '__main__':
    main()
