"""Insecam Fast with longer max_pages and per-page check."""
import os
import re
import time
import json
import urllib.request
import ssl
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

PROGRESS = r'C:\Users\eli6-admin\Documents\eli6-surveillance\insecam_fast_progress.json'
OUT = r'C:\Users\eli6-admin\Documents\eli6-surveillance\insecam_private.json'

# Load progress
progress = {'countries': {}, 'types': {}}
if os.path.exists(PROGRESS):
    try:
        with open(PROGRESS) as fp:
            progress = json.load(fp)
    except:
        pass

lock = threading.Lock()
all_found = {}

# Init from progress
for cc, urls in progress.get('countries', {}).items():
    for url, info in urls.items():
        if not url.startswith('_'):
            all_found[url] = info
for ct, urls in progress.get('types', {}).items():
    for url, info in urls.items():
        if not url.startswith('_'):
            if url not in all_found:
                all_found[url] = info


def fetch(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
        })
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b''
    except Exception as e:
        return -1, b''


def parse_listing_page(html):
    """Parse insecam listing page. Returns list of direct image URLs."""
    urls = []
    # Pattern 1: <a href="/en/view/N/"><img ... src="DIRECT_URL">
    for m in re.finditer(r'<a[^>]+href="/en/view/\d+/?">.*?<img[^>]+src="([^"]+)"', html, re.DOTALL):
        urls.append(m.group(1))
    # Pattern 2: any <img src="...">
    for m in re.finditer(r'<img[^>]+src="(https?://[^"]+)"', html):
        u = m.group(1)
        if u not in urls and ('mjpg' in u or '.jpg' in u or '.m3u8' in u):
            urls.append(u)
    return urls


def scrape_country(country, max_pages=20):
    found = []
    for page in range(1, max_pages + 1):
        pages_done = progress['countries'].get(country, {}).get('_pages_done', 0)
        if page <= pages_done:
            continue
        url = f'https://www.insecam.org/en/bycountry/{country}/?page={page}'
        status, body = fetch(url)
        if status != 200:
            break
        try:
            html = body.decode('utf-8', errors='replace')
        except:
            break
        cams = parse_listing_page(html)
        if not cams:
            break
        for u in cams:
            found.append((u, {'source': f'country:{country}', 'page': page}))
        progress['countries'].setdefault(country, {})['_pages_done'] = page
        time.sleep(0.5)
    return ('country', country, found)


def scrape_type(cam_type, max_pages=20):
    found = []
    for page in range(1, max_pages + 1):
        pages_done = progress['types'].get(cam_type, {}).get('_pages_done', 0)
        if page <= pages_done:
            continue
        url = f'https://www.insecam.org/en/bytype/{cam_type}/?page={page}'
        status, body = fetch(url)
        if status != 200:
            break
        try:
            html = body.decode('utf-8', errors='replace')
        except:
            break
        cams = parse_listing_page(html)
        if not cams:
            break
        for u in cams:
            found.append((u, {'source': f'type:{cam_type}', 'page': page}))
        progress['types'].setdefault(cam_type, {})['_pages_done'] = page
        time.sleep(0.5)
    return ('type', cam_type, found)


def save_progress():
    try:
        # Convert all_found into progress format - PRESERVE all cams and pages
        prog = {'countries': {}, 'types': {}}
        # Copy existing progress structure first
        for src_type in ['countries', 'types']:
            for src_val, v in progress[src_type].items():
                if v.get('_pages_done'):
                    prog[src_type].setdefault(src_val, {})['_pages_done'] = v['_pages_done']
        # Add cams from all_found
        for url, info in all_found.items():
            src = info.get('source', '')
            if ':' in src:
                src_type, src_val = src.split(':', 1)
                key = 'countries' if src_type == 'country' else 'types'
                if url not in prog[key].get(src_val, {}):
                    prog[key].setdefault(src_val, {})[url] = info
        with open(PROGRESS, 'w') as f:
            json.dump(prog, f)
        with open(OUT, 'w') as f:
            json.dump(list(all_found.keys()), f, indent=2)
    except Exception as e:
        print(f'  save err: {e}', flush=True)


def main():
    sys.stdout.reconfigure(line_buffering=True)
    print(f'[Insecam Fast v2] Starting, {len(all_found):,} existing cams', flush=True)

    countries = ['US', 'JP', 'DE', 'IT', 'KR', 'FR', 'GB', 'CA', 'ES', 'MX', 'BR', 'RU',
                 'IN', 'CN', 'TW', 'TH', 'VN', 'ID', 'MY', 'PH', 'AU', 'NZ', 'NL', 'BE',
                 'PL', 'CZ', 'HU', 'AT', 'CH', 'SE', 'NO', 'FI', 'DK', 'IE', 'PT', 'GR',
                 'TR', 'IL', 'AE', 'SA', 'EG', 'ZA', 'NG', 'KE', 'AR', 'CL', 'CO', 'PE',
                 'BG', 'RO', 'RS', 'HR', 'SI', 'UA', 'BY']
    cam_types = ['axis', 'hikvision', 'dahua', 'foscam', 'mobotix', 'panasonic',
                 'sony', 'bosch', 'vivotek', 'arecont', 'pelco']

    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {}
        for c in countries:
            futs[ex.submit(scrape_country, c, 100)] = ('country', c)
        for t in cam_types:
            futs[ex.submit(scrape_type, t, 50)] = ('type', t)

        for f in as_completed(futs):
            src_type, key = futs[f]
            try:
                _, k, found = f.result()
                with lock:
                    for url, info in found:
                        all_found[url] = info
                print(f'  {src_type}:{k}: +{len(found)} (total: {len(all_found):,})', flush=True)
                with lock:
                    save_progress()
            except Exception as e:
                print(f'  {src_type}:{key} err: {e}', flush=True)

    save_progress()
    print(f'\n[Done] {len(all_found):,} cam URLs saved to {OUT}', flush=True)

    # Loop forever: re-scan every 30 min for new cams
    print(f'  Sleeping 30 min before next scan cycle...', flush=True)
    while True:
        time.sleep(1800)
        # Reset progress to re-scan (but preserve _pages_done for completed pages)
        # Re-init all_found from progress
        all_found.clear()
        for cc, urls in progress.get('countries', {}).items():
            for url, info in urls.items():
                if not url.startswith('_'):
                    all_found[url] = info
        for ct, urls in progress.get('types', {}).items():
            for url, info in urls.items():
                if not url.startswith('_'):
                    all_found[url] = info
        print(f'\n[Cycle 2] Starting re-scan, {len(all_found):,} existing cams', flush=True)
        # Re-run main flow (recursive call would be ugly, just break out)
        break


if __name__ == '__main__':
    # Outer loop: re-scan every 30 min
    while True:
        try:
            main()
        except Exception as e:
            print(f'insecam error: {e}', flush=True)
            time.sleep(60)
        # After main() finishes, restart with fresh data
        print(f'\n[insecam] Cycle complete, restarting in 5 min...', flush=True)
        time.sleep(300)
