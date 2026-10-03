"""Shodan InternetDB scanner — queries IPs that already exist in CSV (or seeded lists)
and adds any NEW open cam ports found.

internetdb.shodan.io works without an API key — just per-IP lookups.
"""
import csv
import os
import random
import re
import sys
import time
import urllib.parse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\internetdb_log.txt'

_s = requests.Session()
retries = Retry(total=0)
_s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20))
_s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20))
_s.headers.update({'User-Agent': 'Mozilla/5.0', 'Accept': '*/*'})

# These ASN prefixes tend to host residential IP cams. Subnets are /20 or /24 samples.
ASN_PREFIXES = [
    '23.108', '24.0', '50.197', '73.128', '73.220', '75.64', '76.0', '76.96', '76.121',
    '84.0', '87.139', '88.0', '89.0', '91.0', '92.0', '94.0', '95.0', '97.0',
    '104.0', '108.0', '109.0', '172.0', '174.0', '176.0', '178.0', '188.0',
    '189.0', '190.0', '192.0', '195.0', '198.0', '201.0', '213.0',
    # RIPE
    '46.0', '62.0', '77.0', '78.0', '82.0', '83.0',
]


def get_existing_hosts():
    """Collect IPs already in CSV."""
    ips = set()
    if not os.path.exists(CSV_PATH):
        return ips
    with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    for row in rows[1:]:
        for cell in row:
            if not cell:
                continue
            for m in re.finditer(r'(?:https?|rtsp|rtmp|mms)://(\d{1,3}(?:\.\d{1,3}){3})(?::(\d+))?', cell, re.I):
                ips.add(m.group(1))
    return ips


def random_ips_from_prefix(prefix, n):
    """Take a 3-octet prefix and generate n IPs in /24 ranges."""
    ips = set()
    for _ in range(n * 4):
        try:
            x = random.randint(0, 254)
            y = random.randint(0, 254)
            ips.add(f'{prefix}.{x}.{y}')
            if len(ips) >= n:
                break
        except Exception:
            pass
    return list(ips)


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def main():
    import harvest_lib, probe_lib, csv_writer

    existing = get_existing_hosts()
    log(f'[init] {len(existing)} existing IPs in CSV')

    # Take first 200 random IPs not in existing
    candidates = []
    for pref in ASN_PREFIXES:
        candidates.extend(random_ips_from_prefix(pref, 50))
    random.shuffle(candidates)
    candidates = candidates[:500]
    candidates = [c for c in candidates if c not in existing]
    log(f'[query] {len(candidates)} new candidate IPs')

    cam_ports_set = set([80, 8080, 8081, 8090, 8000, 8001, 8888, 10000, 88, 888])

    hits = []
    n = 0
    for ip in candidates:
        n += 1
        try:
            r = _s.get(f'https://internetdb.shodan.io/{ip}', timeout=6)
            if r.status_code != 200:
                continue
            j = r.json()
            ports = j.get('ports', []) or []
            tags = j.get('tags', []) or []
            cnames = j.get('cpes', []) or []
            # Filter to cam-like (port in cam_ports_set) OR (tags contain webcam/ipcam/cam)
            interesting = False
            # Open ports that could host webcams (broader set)
            cam_port_set = {80, 443, 8080, 8081, 8090, 8000, 8001, 8888, 10000, 88, 888, 8165, 10510, 10520, 81, 82, 83, 84, 85, 86, 8002, 8008, 8800, 8801, 8088, 8082, 8083, 8084, 8085, 8086, 8089, 8765, 9999}
            for p in ports:
                if p in cam_port_set:
                    interesting = True
                    break
            if not interesting:
                for t in tags:
                    if any(k in t.lower() for k in ('cam', 'video', 'ipcam', 'stream', 'rtsp', 'webcam', 'ipcam', 'nvr')):
                        interesting = True
                        break
            if interesting:
                log(f'  IP-MATCH {ip}: ports={ports}, tags={tags}')
                hits.append((ip, ports, tags))
        except Exception:
            pass
        if n % 50 == 0:
            log(f'   progress {n}/{len(candidates)} hits={len(hits)}')
        # 0.1s delay
        time.sleep(0.1)

    log(f'[probe] probing {len(hits)} hits for live streams')
    for ip, ports, tags in hits:
        # Probe each cam port
        for p in ports:
            if p not in cam_ports_set:
                continue
            res = probe_lib.probe_host(_s, ip, p, False, 3.0)
            if res:
                log(f'   LIVE {ip}:{p} {res["family"]} {res["url"][:120]}')
                try:
                    geo = probe_lib.geoip(_s, ip)
                except Exception:
                    geo = {}
                entry = csv_writer.entry_from_probe(res, {'source': 'internetdb'}, geo)
                try:
                    idx = csv_writer.append_one(entry)
                    log(f'   ADDED idx={idx}: {entry["project_name"][:80]}')
                except Exception as e:
                    log(f'   err: {e}')
                time.sleep(1.4)
                break

    log(f'[done] {len(hits)} IP hits; cams may have been added')


if __name__ == '__main__':
    main()
