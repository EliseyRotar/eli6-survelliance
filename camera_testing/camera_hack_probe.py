"""Probe URLs from insecam_live_cams.txt and add live ones to CSV.

Reads .txt, dedupes against CSV, then probes each URL with probe_lib.
Appends only NEW live cams to CSV.
"""
import csv
import os
import random
import re
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

UA = 'Mozilla/5.0'
CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\camera_hack_probe_log.txt'
TXT_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\insecam_live_cams.txt'

sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')
import probe_lib
import csv_writer


def session():
    s = requests.Session()
    retries = Retry(total=0)
    s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=80, pool_maxsize=80))
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=80, pool_maxsize=80))
    s.headers.update({'User-Agent': UA})
    return s


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


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


def main():
    s = session()
    seen = existing_hosts()
    log(f'[init] {len(seen)} existing hosts')

    if not os.path.exists(TXT_PATH):
        log('[err] no TXT file')
        return
    urls = []
    with open(TXT_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            u = line.strip()
            if not u:
                continue
            urls.append(u)
    log(f'[load] {len(urls)} URLs from txt')

    # Dedup host
    targets = []
    for u in urls:
        m = re.match(r'https?://([^/]+)/?(\S*)', u)
        if not m:
            continue
        host_port = m.group(1)
        if host_port in seen:
            continue
        targets.append(u)

    log(f'[probe targets] {len(targets)}')

    found = 0
    n = 0
    with ThreadPoolExecutor(max_workers=40) as ex:
        futs = {}
        for u in targets:
            m = re.match(r'https?://([^/]+)/?(\S*)', u)
            if not m:
                continue
            host_port = m.group(1)
            hp = host_port.split(':')
            host = hp[0]
            port = int(hp[1]) if len(hp) > 1 else 80
            base = f'http://{host}:{port}'
            futs[ex.submit(probe_lib.probe_host, s, host, port, False, 2.5)] = (u, host, port)
        for fut in as_completed(futs):
            n += 1
            u, host, port = futs[fut]
            try:
                res = fut.result(timeout=8)
            except Exception:
                continue
            if res and res['weight'] >= 30:
                log(f'  HIT {res["url"][:100]} w={res["weight"]}')
                # Use original URL if it has a specific path
                try:
                    geo = probe_lib.geoip(s, host)
                except Exception:
                    geo = {}
                entry = csv_writer.entry_from_probe(res, {'source': 'insecam_dump'}, geo)
                try:
                    idx_csv = csv_writer.append_one(entry)
                    log(f'    ADDED idx={idx_csv}')
                    found += 1
                except Exception as e:
                    log(f'    err: {e}')
                time.sleep(0.5)
            if n % 100 == 0:
                log(f'  progress {n}/{len(targets)}, found={found}')


if __name__ == '__main__':
    main()
