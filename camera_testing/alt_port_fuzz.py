"""Probe additional ports on cams we already know live. Each cam has its (host,port) known.
We try other common cam ports on the same host.
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

UA_LIST = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 Safari/605.1.15',
    'curl/8.4.0',
]

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\alt_port_log.txt'

sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')
import probe_lib, csv_writer

_s = requests.Session()
retries = Retry(total=0)
_s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20))
_s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20))
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

    # Hosts (with their known live port)
    knowns = {}  # host -> set of known ports
    for row in rows[1:]:
        host = row[host_col].strip() if host_col < len(row) else ''
        if not host:
            continue
        live = row[live_col].strip() if live_col < len(row) else ''
        ports = set()
        for m in re.finditer(r'://[^:]+:(\d+)', live):
            ports.add(int(m.group(1)))
        # Also strip hostnames that include a port
        knowns.setdefault(host, ports)

    log(f'[init] {len(knowns)} hosts')

    alt_ports = [80, 8080, 81, 82, 8000, 8081, 8082, 8088, 8090, 8888, 88, 888, 10000]

    n = 0
    found = 0
    for host, known_ports in list(knowns.items()):
        n += 1
        for p in alt_ports:
            if p in known_ports:
                continue
            res = probe_lib.probe_host(_s, host, p, False, 2.5)
            if res:
                # only add if weight is reasonable
                if res['weight'] < 35:
                    continue
                log(f'  ALT-HIT {host}:{p} {res["family"]} {res["url"][:100]}')
                try:
                    geo = probe_lib.geoip(_s, host)
                except Exception:
                    geo = {}
                entry = csv_writer.entry_from_probe(res, {'source': 'alt_port_fuzz'}, geo)
                try:
                    idx = csv_writer.append_one(entry)
                    log(f'  ADDED idx={idx}: {entry["project_name"][:80]}')
                    found += 1
                except Exception as e:
                    log(f'  err: {e}')
                time.sleep(1.4)
                break  # one alt per host per cycle

        if n % 30 == 0:
            log(f'[progress] {n}/{len(knowns)} hosts, {found} alt added')

    log(f'[done] {found} alt-port new live cams')


if __name__ == '__main__':
    main()
