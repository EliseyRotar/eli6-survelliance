"""Brand fingerprint enrichment — runs after a cam is appended to CSV.

For each row, detect server banner / path hits and update fields:
- server_header
- brand, model
- description (rich text)
- notes (CVE references)
"""
import csv
import os
import re
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')
sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\bruteforce')
import probe_lib
from vendor_cves import VENDOR_CVES, BRAND_BANNERS, FINGERPRINT_ENDPOINTS

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\brand_enrichment_log.txt'

UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126.0.0.0'

_crawl_lock_path = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\enrichment.lock'
_crawl_done_path = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\enrichment.done'
import threading
_lock = threading.Lock()


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def session():
    s = requests.Session()
    retries = Retry(total=0)
    s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20))
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20))
    s.headers.update({'User-Agent': UA, 'Accept': '*/*'})
    return s


def fingerprint_one(s, host, port):
    """Probe a single host for brand fingerprint. Return dict with brand/model/server/cves."""
    out = {'host': host, 'port': port, 'brand': '', 'model': '', 'server_header': '', 'cves': []}
    base = f'http://{host}:{port}'
    try:
        # 1. GET /
        r = s.get(base, timeout=4, verify=False, allow_redirects=False)
        server_h = r.headers.get('Server', '')
        out['server_header'] = server_h
        # body
        body = r.text
        server_h_l = server_h.lower()
        body_l = body.lower()

        # 2. Match brands
        for brand, sigs in BRAND_BANNERS.items():
            matched = False
            for sig in sigs:
                if sig.lower() in server_h_l or sig.lower() in body_l:
                    matched = True
                    break
            if matched:
                out['brand'] = brand
                break

        # 3. If brand identified, query fingerprint endpoint
        if out['brand'] and out['brand'] in FINGERPRINT_ENDPOINTS:
            for path, label in FINGERPRINT_ENDPOINTS[out['brand']]:
                try:
                    r2 = s.get(base + path, timeout=3, verify=False)
                    if r2.status_code == 200:
                        # Look for model serial
                        if out['brand'] == 'hikvision':
                            m = re.search(r'<model>([^<]+)</model>', r2.text)
                            if m:
                                out['model'] = m.group(1).strip()
                        elif out['brand'] == 'dahua':
                            m = re.search(r'<model>([^<]+)</model>', r2.text) or re.search(r'version[^"]*"([^"]+)"', r2.text)
                            if m:
                                out['model'] = m.group(1).strip()
                        elif out['brand'] == 'axis':
                            m = re.search(r'^root\.Model\s*=\s*(.+)$', r2.text, re.M)
                            if m:
                                out['model'] = m.group(1).strip()
                except Exception:
                    pass
        # 4. CVEs
        if out['brand']:
            out['cves'] = VENDOR_CVES.get(out['brand'], [])
    except Exception:
        pass
    return out


def update_row(idx, info):
    """Update a single CSV row in-place (atomic)."""
    with _lock:
        if os.path.exists(_crawl_lock_path):
            return False
        with open(_crawl_lock_path, 'w') as f:
            f.write('1')

    try:
        with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
            rows = list(csv.reader(f))
        header = rows[0]
        # Find row by idx
        idx_col = header.index('idx')
        server_col = header.index('server_header')
        brand_col = header.index('brand')
        model_col = header.index('model')
        notes_col = header.index('notes')
        desc_col = header.index('description')

        for ri, row in enumerate(rows):
            if ri == 0:
                continue
            if row and row[idx_col] == str(idx):
                old = list(row)
                old[server_col] = info.get('server_header', '')[:200]
                old[brand_col] = info.get('brand', '')
                old[model_col] = info.get('model', '')[:200]
                if info.get('cves'):
                    cves_str = ', '.join(info['cves'][:6])
                    old[notes_col] = (old[notes_col] or '') + f' | Vulns: {cves_str}'
                # If desc empty, attach fingerprint description
                if not old[desc_col] or len(old[desc_col]) < 30:
                    old[desc_col] = (
                        f"{info.get('brand', '').title()} camera at port {info.get('port', '')}. "
                        f"Server: {info.get('server_header', '') or 'unknown'}. "
                        f"{('Model: ' + info['model']) if info.get('model') else ''} "
                        f"{('Known CVEs: ' + ', '.join(info['cves'][:6])) if info.get('cves') else ''}".strip()
                    )
                rows[ri] = old
                break

        tmp = CSV_PATH + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
            for r in rows:
                w.writerow(r)
        os.replace(tmp, CSV_PATH)
        return True
    finally:
        try:
            os.remove(_crawl_lock_path)
        except OSError:
            pass


def main():
    s = session()
    if not os.path.exists(CSV_PATH):
        log('[init] no CSV')
        return
    with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    header = rows[0]
    if 'idx' not in header or 'live_stream_url' not in header:
        log('[init] missing columns')
        return
    idx_col = header.index('idx')
    live_col = header.index('live_stream_url')
    host_col = header.index('host')
    brand_col = header.index('brand')

    # Pick rows that don't have a brand yet
    targets = []
    seen_keys = set()
    for r in rows[1:]:
        if len(r) < len(header):
            continue
        if r[idx_col] and r[brand_col]:
            continue  # already enriched
        idx = r[idx_col]
        if idx:
            targets.append((idx, r[host_col], r[live_col]))
            seen_keys.add(idx)

    log(f'[init] {len(targets)} rows to enrich')

    # Run threading
    pool_work = []
    with ThreadPoolExecutor(max_workers=12) as ex:
        for idx, host, live in targets:
            if not host:
                continue
            # Find port from live
            m = re.search(r':(\d+)', host)
            port = int(m.group(1)) if m else 80
            pool_work.append((idx, host, port))

        futs = {ex.submit(fingerprint_one, s, h, p): (idx, h, p) for (idx, h, p) in pool_work}
        n = 0
        for fut in as_completed(futs):
            n += 1
            idx, h, p = futs[fut]
            try:
                info = fut.result(timeout=12)
            except Exception as e:
                log(f'  [{idx}] {h}:{p} err: {e}')
                continue
            if info['brand']:
                log(f'  [{idx}] {h}:{p} brand={info["brand"]} model={info["model"]} server={info["server_header"][:50]}')
                try:
                    update_row(idx, info)
                except Exception as e:
                    log(f'  [{idx}] update err: {e}')
            if n % 50 == 0:
                log(f'  progress {n}/{len(pool_work)}')

    with open(_crawl_done_path, 'w') as f:
        f.write(time.strftime('%H:%M:%S'))
    log('[done]')


if __name__ == '__main__':
    main()
