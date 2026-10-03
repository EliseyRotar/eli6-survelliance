"""Take ALL known hosts from CSV and try *all* webcam ports × *all* patterns.
Unlike alt_port_fuzz this scans ALL alt ports per host.
"""
import csv
import os
import random
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

UA_LIST = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 Safari/605.1.15',
    'curl/8.4.0',
]

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\full_reprobe_log.txt'

sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')
import probe_lib, csv_writer

_s = requests.Session()
retries = Retry(total=0)
_s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=40, pool_maxsize=40))
_s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=40, pool_maxsize=40))
_s.headers.update({'User-Agent': random.choice(UA_LIST), 'Accept': '*/*'})


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def main():
    if not os.path.exists(CSV_PATH):
        log('no CSV')
        return

    with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    header = rows[0]
    if 'live_stream_url' not in header or 'host' not in header:
        log('missing cols')
        return
    live_col = header.index('live_stream_url')
    host_col = header.index('host')

    # Re-collect hosts
    knowns = {}
    for row in rows[1:]:
        host = row[host_col].strip() if host_col < len(row) else ''
        if not host:
            continue
        knowns[host] = True

    log(f'[init] {len(knowns)} hosts to mass-fuzz')

    # Each host gets all ports
    all_ports = [80, 81, 82, 83, 84, 85, 86, 88, 8000, 8001, 8002, 8008, 8080, 8081, 8082, 8083, 8084, 8085, 8086, 8088, 8089, 8090, 8888, 8800, 888, 10000, 5000, 5910]

    cands = []
    for host in knowns:
        for p in all_ports:
            cands.append({'host': host, 'port': p, 'ssl': False, 'source': 'full-reprobe'})

    log(f'[cands] {len(cands)} (host × port combos)')

    found = 0
    probed = 0
    with ThreadPoolExecutor(max_workers=80) as ex:
        futs = []
        for c in cands:
            futs.append(ex.submit(probe_lib.probe_host, _s, c['host'], c['port'], False, 2.0))
        for fut in as_completed(futs):
            probed += 1
            try:
                res = fut.result(timeout=8)
            except Exception:
                res = None
            if res and res['weight'] >= 35:
                log(f'  HIT {res["host"]}:{res["port"]} {res["family"]} {res["url"][:80]}')
                try:
                    geo = probe_lib.geoip(_s, res['host'])
                except Exception:
                    geo = {}
                entry = csv_writer.entry_from_probe(res, {'source': 'full-reprobe'}, geo)
                try:
                    idx = csv_writer.append_one(entry)
                    found += 1
                    log(f'  ADDED idx={idx}: {entry["project_name"][:80]}')
                except Exception as e:
                    log(f'  err: {e}')
                time.sleep(1.4)
            if probed % 1000 == 0:
                log(f'[progress] {probed}/{len(cands)}, found {found}')

    log(f'[done] {found} new live cams found via full-reprobe')


if __name__ == '__main__':
    main()
