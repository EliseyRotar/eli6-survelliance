"""Re-probe existing CSV entries for *better* or *additional* live URLs.

For every cam in the CSV, probe patterns NOT already in live_stream_url.
Adds new rows (a child cam) when a different/better path works.
"""
import csv
import json
import os
import random
import re
import sys
import time
import urllib.parse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

UA_LIST = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) Chrome/126.0.0.0 Safari/537.36',
    'curl/8.4.0',
]

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\reprobe_log.txt'

sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')
import probe_lib, csv_writer

_s = requests.Session()
retries = Retry(total=0)
_s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=30, pool_maxsize=30))
_s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=30, pool_maxsize=30))
_s.headers.update({'User-Agent': random.choice(UA_LIST), 'Accept': '*/*'})


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def extract_host_port(url):
    m = re.match(r'(?:https?|rtsp|rtmp|mms)://([^/]+)(?::(\d+))?(/.*)?', url)
    if not m:
        return None, None, None
    host = m.group(1).lower()
    port = int(m.group(2)) if m.group(2) else (443 if url.startswith('https') else 80)
    path = m.group(3) or '/'
    return host, port, path


def main():
    with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    header = rows[0]
    if 'live_stream_url' not in header or 'host' not in header:
        log('missing columns')
        return
    live_col = header.index('live_stream_url')
    host_col = header.index('host')
    src_label = 'reprobe'
    seed_hosts = {}
    for row in rows[1:]:
        host = row[host_col].strip() if host_col < len(row) else ''
        if not host:
            continue
        live_urls_str = row[live_col].strip() if live_col < len(row) else ''
        paths_used = set()
        for u in re.findall(r'(?:https?|rtsp|rtmp)://[^/]+(/\S*)', live_urls_str):
            paths_used.add(u.split('?')[0])
        if host not in seed_hosts:
            seed_hosts[host] = paths_used

    log(f'[init] {len(seed_hosts)} unique hosts to re-probe')

    found = 0
    n = 0
    for host, paths_used in list(seed_hosts.items()):
        n += 1
        # Only try *one* alt port per host to keep budget low
        for port in [8080, 8000, 888, 8090, 10000]:
            res = probe_lib.probe_host(_s, host, port, False, 2.5)
            if res and not any(p in res['url'] for p in paths_used):
                log(f'  NEWHIT {host}:{port} {res["family"]} {res["url"][:120]}')
                try:
                    geo = probe_lib.geoip(_s, host)
                except Exception:
                    geo = {}
                entry = csv_writer.entry_from_probe(res, {'source': 'reprobe'}, geo)
                try:
                    idx = csv_writer.append_one(entry)
                    log(f'  ADDED idx={idx}: {entry["project_name"][:80]}')
                    found += 1
                except Exception as e:
                    log(f'  err: {e}')
                time.sleep(1.4)
                break  # one new hit per host
        if n % 30 == 0:
            log(f'[progress] {n}/{len(seed_hosts)} hosts reprobed, {found} new')

    log(f'[done] {found} new live URLs added via reprobe')


if __name__ == '__main__':
    main()
