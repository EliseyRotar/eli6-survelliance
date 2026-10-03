"""Continuous cam-discovery loop. Heavy-duty: many sources, never returns."""
import csv
import json
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
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0.0.0 Safari/537.36',
    'curl/8.4.0',
]

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\pipeline_log.txt'

# Limit per round (won't spawn thousands of futures at once)
PROBE_BATCH_SIZE = 80
MAX_THREADS = 20
MAX_PATHS_PER_HOST = 14  # probe only the top 14 patterns
PROBE_TIMEOUT = 3.0


def session(pool=120):
    s = requests.Session()
    retries = Retry(total=0, backoff_factor=0.0, status_forcelist=[])
    s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=pool, pool_maxsize=pool))
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=pool, pool_maxsize=pool))
    s.headers.update({'User-Agent': random.choice(UA_LIST), 'Accept': '*/*'})
    return s


_log_lock = None
def _ll():
    global _log_lock
    if _log_lock is None:
        import threading
        _log_lock = threading.Lock()
    return _log_lock


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    with _ll():
        try:
            with open(LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(line + '\n')
        except Exception:
            pass
        try:
            print(line, flush=True)
        except Exception:
            try:
                line_clean = line.encode('ascii', 'replace').decode('ascii')
                print(line_clean, flush=True)
            except Exception:
                pass


def existing_hosts():
    if not os.path.exists(CSV_PATH):
        return set()
    seen = set()
    with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    for row in rows[1:]:
        for cell in row:
            if not cell:
                continue
            for m in re.finditer(r'(?:https?|rtsp|rtmp|mms)://([a-z0-9\-\.]+)(?::(\d+))?', cell, re.I):
                h = m.group(1).lower()
                seen.add(h)
                seen.add(f'{h}:{m.group(2) or 80}')
    return seen


def probe_one(s, host, port, ssl=False, timeout=PROBE_TIMEOUT):
    """Probe a host with a *short* list of high-yield paths. Returns best live or None."""
    sys.path.insert(0, os.path.dirname(__file__))
    import probe_lib
    # Use only top-12 patterns by weight to avoid per-host explosion
    patterns = sorted(probe_lib.PROBE_PATTERNS, key=lambda x: -x[1])[:MAX_PATHS_PER_HOST]
    scheme = 'https' if ssl else 'http'
    base = f'{scheme}://{host}:{port}'
    best = None
    best_w = -1
    for path, weight, fam in patterns:
        url = base + path
        try:
            r = s.get(url, timeout=timeout, allow_redirects=False, stream=False, verify=False)
            ct = r.headers.get('Content-Type', '').lower()
            cl = r.headers.get('Content-Length', '0')
            try:
                cl_n = int(cl)
            except Exception:
                cl_n = 0
            if r.status_code in (301, 302):
                continue
            if r.status_code in (401, 403):
                continue
            if r.status_code in (404, 500, 502, 503, 504):
                continue
            if r.status_code == 200:
                body = r.content[:8192]
                kind, w = probe_lib.looks_like_live(r.headers, body)
                if kind is None:
                    continue
                eff = weight + w
                if eff > best_w:
                    best_w = eff
                    best = {
                        'url': url,
                        'family': fam,
                        'stream_kind': kind,
                        'content_type': ct,
                        'content_length': cl_n,
                        'weight': eff,
                        'host': host,
                        'port': port,
                        'ssl': ssl,
                        'http_status': 200,
                    }
                if best_w >= 80:
                    return best
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError,
                requests.exceptions.Timeout, requests.exceptions.RequestException,
                requests.exceptions.ChunkedEncodingError,
                ConnectionResetError, OSError, Exception):
            pass
    return best


def process_round(s, src_label, cands, seen, seed_ips):
    """Probe `cands` (a list of {host,port,ssl,source}) in batches. Returns list of (cam_d, probe_res)."""
    sys.path.insert(0, os.path.dirname(__file__))
    import probe_lib
    import csv_writer

    # Dedup in-batch
    seen_this_batch = set()
    unique = []
    extra_cands = []
    for c in cands:
        key = f'{c["host"]}:{c["port"]}'
        if key in seen_this_batch or key in seen:
            continue
        seen_this_batch.add(key)
        unique.append(c)
        # Also try alt ports on same host for any new IP
        for alt_p in [80, 8080, 8000, 8090, 8081]:
            if alt_p == c['port']:
                continue
            k2 = f'{c["host"]}:{alt_p}'
            if k2 not in seen_this_batch and k2 not in seen:
                seen_this_batch.add(k2)
                extra_cands.append({'host': c['host'], 'port': alt_p, 'ssl': False, 'source': c['source'] + '+alt'})
    unique.extend(extra_cands)

    found = []
    if not unique:
        return found

    # Probe in batches of PROBE_BATCH_SIZE
    for i in range(0, len(unique), PROBE_BATCH_SIZE):
        batch = unique[i:i+PROBE_BATCH_SIZE]
        with ThreadPoolExecutor(max_workers=min(MAX_THREADS, len(batch))) as ex:
            futs = {ex.submit(probe_one, s, c['host'], c['port'], c.get('ssl', False), PROBE_TIMEOUT): c for c in batch}
            for fut in as_completed(futs):
                c = futs[fut]
                try:
                    res = fut.result(timeout=PROBE_TIMEOUT + 8)
                except Exception:
                    continue
                if res:
                    res['_source'] = src_label
                    res['_src_cand'] = c
                    found.append(res)
                    log(f'  HIT {res["host"]}:{res["port"]} {res["family"]} kind={res["stream_kind"]} w={res["weight"]}')

        # Append each found before processing next batch
        for res in found[-len(batch):]:
            seen.add(f'{res["host"]}:{res["port"]}')
            seed_ips.add(res['host'])
            try:
                geo = probe_lib.geoip(s, res['host'])
            except Exception:
                geo = {}
            entry = csv_writer.entry_from_probe(res, res.get('_src_cand', {}), geo)
            try:
                idx = csv_writer.append_one(entry)
                log(f'  ADDED idx={idx}: {entry["project_name"][:80]}')
            except Exception as e:
                log(f'  CSV append err: {e}')
            time.sleep(1.4)  # ip-api rate

    log(f'[{src_label}] found {len(found)} live cams in this round')
    return found


def run_forever():
    sys.path.insert(0, os.path.dirname(__file__))
    import harvest_lib

    s = session()
    seen = existing_hosts()
    log(f'[init] CSV has {len(seen)} host keys pre-existing')

    seed_ips = set()
    for h in seen:
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', h):
            seed_ips.add(h)

    cycles = [
        ('insecam-EU', lambda: harvest_lib.fetch_insecam_region(s, 'EU')),
        ('insecam-AS', lambda: harvest_lib.fetch_insecam_region(s, 'AS')),
        ('insecam-AM', lambda: harvest_lib.fetch_insecam_region(s, 'AM')),
        ('insecam-OC', lambda: harvest_lib.fetch_insecam_region(s, 'OC')),
        ('insecam-AF', lambda: harvest_lib.fetch_insecam_region(s, 'AF')),
        ('insecam-brands', lambda: harvest_lib.fetch_insecam_brands(s)),
        ('insecam-cities', lambda: harvest_lib.fetch_insecam_cities(s)),
        ('indexers', lambda: harvest_lib.fetch_indexers(s)),
        ('internetdb', lambda: harvest_lib.fetch_internetdb_hits(s, n=300)),
    ]

    rnd = 0
    cycle_idx = -1
    while True:
        rnd += 1
        cycle_idx = (cycle_idx + 1) % len(cycles)
        name, fn = cycles[cycle_idx]
        log(f'[round {rnd}] source={name}')

        try:
            raw = fn()
        except Exception as e:
            log(f'[round {rnd}] {name} err: {e}')
            time.sleep(5)
            continue

        cands = harvest_lib.normalize(raw, name, seen)
        log(f'[round {rnd}] {len(cands)} new candidates after dedup')

        if cands:
            process_round(s, name, cands, seen, seed_ips)

        time.sleep(2)


if __name__ == '__main__':
    try:
        run_forever()
    except KeyboardInterrupt:
        log('Keyboard interrupt - exiting')
