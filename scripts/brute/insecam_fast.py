"""Fast insecam scraper - uses listing pages only, no per-cam visits.

Insecam listing pages contain enough info (URL, type) without needing to visit
each cam page individually.
"""
import os
import re
import time
import json
import urllib.request
import ssl
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

PROGRESS = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\insecam_fast_progress.json'
OUT = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\insecam_private.json'

# Load existing progress
progress = {'countries': {}, 'types': {}}
if os.path.exists(PROGRESS):
    try:
        with open(PROGRESS) as f:
            progress = json.load(f)
    except:
        pass

# Thread-safe counter
lock = threading.Lock()
all_found = {}  # url -> {type, country, city, cam_id, source}

# Init from progress
for cc, urls in progress.get('countries', {}).items():
    for url, info in urls.items():
        all_found[url] = info
for ct, urls in progress.get('types', {}).items():
    for url, info in urls.items():
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
    except Exception:
        return -1, b''


def parse_listing_page(html, source_type, source_value):
    """Parse insecam listing page. Returns list of (cam_id, direct_url, info)."""
    cams = []
    # Pattern 1: <a href="/en/view/N/"><img ... src="DIRECT_URL">
    for m in re.finditer(r'<a[^>]+href="/en/view/(\d+)/?"[^>]*>.*?<img[^>]+src="([^"]+)"', html, re.DOTALL):
        cam_id = m.group(1)
        direct_url = m.group(2)
        cams.append((cam_id, direct_url, source_type, source_value))
    # Pattern 2: <img id="liveCam" ... src="URL">
    for m in re.finditer(r'<img[^>]+id="liveCam"[^>]+src="([^"]+)"', html):
        cams.append(('?', m.group(1), source_type, source_value))
    return cams


def scrape_country(country, max_pages=10):
    """Scrape cams by country."""
    found = []
    for page in range(1, max_pages + 1):
        if page <= progress['countries'].get(country, {}).get('_pages_done', 0):
            continue
        url = f'https://www.insecam.org/en/bycountry/{country}/?page={page}'
        status, body = fetch(url)
        if status != 200:
            break
        try:
            html = body.decode('utf-8', errors='replace')
        except:
            break
        cams = parse_listing_page(html, 'country', country)
        if not cams:
            break
        for cam_id, direct_url, src_type, src_val in cams:
            found.append((direct_url, {'source': f'{src_type}:{src_val}', 'cam_id': cam_id}))
        # Mark page done
        progress['countries'].setdefault(country, {})
        progress['countries'][country]['_pages_done'] = page
        time.sleep(0.3)
    return country, found


def scrape_type(cam_type, max_pages=10):
    """Scrape cams by type/brand."""
    found = []
    for page in range(1, max_pages + 1):
        if page <= progress['types'].get(cam_type, {}).get('_pages_done', 0):
            continue
        url = f'https://www.insecam.org/en/bytype/{cam_type}/?page={page}'
        status, body = fetch(url)
        if status != 200:
            break
        try:
            html = body.decode('utf-8', errors='replace')
        except:
            break
        cams = parse_listing_page(html, 'type', cam_type)
        if not cams:
            break
        for cam_id, direct_url, src_type, src_val in cams:
            found.append((direct_url, {'source': f'{src_type}:{src_val}', 'cam_id': cam_id}))
        progress['types'].setdefault(cam_type, {})
        progress['types'][cam_type]['_pages_done'] = page
        time.sleep(0.3)
    return cam_type, found


def main():
    sys.stdout.reconfigure(line_buffering=True)
    print(f'[Insecam Fast] Starting, {len(all_found):,} existing cams', flush=True)

    countries = ['US', 'JP', 'DE', 'IT', 'KR', 'FR', 'GB', 'CA', 'ES', 'MX', 'BR', 'RU',
                 'IN', 'CN', 'TW', 'TH', 'VN', 'ID', 'MY', 'PH', 'AU', 'NZ', 'NL', 'BE',
                 'PL', 'CZ', 'HU', 'AT', 'CH', 'SE', 'NO', 'FI', 'DK', 'IE', 'PT', 'GR',
                 'TR', 'IL', 'AE', 'SA', 'EG', 'ZA', 'NG', 'KE', 'AR', 'CL', 'CO', 'PE',
                 'BG', 'RO', 'RS', 'HR', 'SI', 'UA', 'BY']
    cam_types = ['axis', 'hikvision', 'dahua', 'foscam', 'mobotix', 'panasonic',
                 'sony', 'bosch', 'vivotek', 'arecont', 'pelco']

    # Run countries + types in parallel
    tasks = [(c,) for c in countries] + [(t,) for t in cam_types]

    with ThreadPoolExecutor(max_workers=8) as ex:
        # Submit countries
        futs = {}
        for c in countries:
            futs[ex.submit(scrape_country, c, 5)] = ('country', c)
        for t in cam_types:
            futs[ex.submit(scrape_type, t, 5)] = ('type', t)

        for f in as_completed(futs):
            src_type, key = futs[f]
            try:
                k, found = f.result()
                with lock:
                    for url, info in found:
                        all_found[url] = info
                    if src_type == 'country':
                        for url, info in found:
                            progress['countries'].setdefault(k, {})[url] = info
                    else:
                        for url, info in found:
                            progress['types'].setdefault(k, {})[url] = info
                print(f'  {src_type}:{k}: +{len(found)} cams (total: {len(all_found):,})', flush=True)
            except Exception as e:
                print(f'  {src_type}:{key} err: {e}', flush=True)

            # Save progress every task
            with lock:
                try:
                    with open(PROGRESS, 'w') as f:
                        json.dump(progress, f)
                    with open(OUT, 'w') as f:
                        json.dump(list(all_found.keys()), f, indent=2)
                except Exception as e:
                    print(f'  save err: {e}', flush=True)

    print(f'\n[Done] {len(all_found):,} cam URLs saved to {OUT}', flush=True)


if __name__ == '__main__':
    main()
