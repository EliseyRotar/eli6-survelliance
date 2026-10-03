"""Simple insecam country loop - flushes stdout, one country at a time."""
import csv
import os
import sys
import time
import json
import re
import urllib.request
import ssl
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

import glob

# Force unbuffered
sys.stdout.reconfigure(line_buffering=True)

CSV_PATH = None
for f in glob.glob(r'C:\Users\eli6-admin\Documents\**/controllable_Webcams.csv', recursive=True):
    CSV_PATH = f
    break
if not CSV_PATH:
    print('CSV not found')
    exit(1)
print(f'CSV: {CSV_PATH}', flush=True)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def fetch(url, timeout=8):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, r.headers.get('Content-Type', ''), r.read()
    except urllib.error.HTTPError as e:
        return e.code, '', b''
    except Exception as e:
        return -1, str(e)[:100], b''


def detect_video_type(url, content_type):
    url_lower = url.lower()
    if 'mjpg/' in url_lower or 'multipart' in content_type:
        return 'video-mjpeg'
    if 'faststream' in url_lower or 'cam_1.cgi' in url_lower:
        return 'video-mjpeg'
    if 'axis-cgi/mjpg' in url_lower:
        return 'video-mjpeg'
    if '.m3u8' in url_lower:
        return 'video-hls'
    if '.mp4' in url_lower:
        return 'video-mp4'
    if 'video.cgi' in url_lower:
        return 'video-mjpeg'
    if content_type.startswith('multipart/'):
        return 'video-mjpeg'
    if content_type.startswith('image/'):
        return 'image'
    return 'unknown'


def scrape_one_country(cc, max_pages=3):
    """Scrape one country, return list of (cam_id, country, direct_url)."""
    cam_ids = []
    for page in range(1, max_pages + 1):
        url = f'https://www.insecam.org/en/bycountry/{cc}/?page={page}'
        status, ct, body = fetch(url, timeout=8)
        if status != 200:
            break
        try:
            html = body.decode('utf-8', errors='replace')
        except:
            break
        for m in re.finditer(r'href="(/en/view/(\d+)/?)"', html):
            cam_id = m.group(2)
            cam_ids.append((cam_id, cc))
        if not cam_ids:
            break
    # Get direct URLs in parallel
    direct = []
    def visit(cam_id, country):
        u = f'https://www.insecam.org/en/view/{cam_id}/'
        status, ct, body = fetch(u, timeout=5)
        if status != 200:
            return None
        try:
            html = body.decode('utf-8', errors='replace')
        except:
            return None
        m = re.search(r'<img[^>]+id="image0"[^>]+src="([^"]+)"', html)
        if not m:
            m = re.search(r'<img[^>]+src="(https?://[^"]+\.jpg)"', html)
        if m:
            return (cam_id, country, m.group(1))
        return None

    with ThreadPoolExecutor(max_workers=20) as ex:
        futs = {ex.submit(visit, cid, cc): cid for cid, cc in cam_ids}
        for f in as_completed(futs):
            try:
                r = f.result(timeout=8)
                if r:
                    direct.append(r)
            except Exception:
                pass
    return direct


def probe_and_add(rows, existing):
    """Probe URLs and add live ones to CSV."""
    # Probe
    rows_to_add = []
    with ThreadPoolExecutor(max_workers=40) as ex:
        def probe(row):
            cid, country, url = row
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=4, context=ctx) as r:
                    data = r.read(512*1024)
                    ct = r.headers.get('Content-Type', '')
                    server = r.headers.get('Server', '')
                    if r.status == 200:
                        return (cid, country, url, ct, server, detect_video_type(url, ct))
            except Exception:
                pass
            return None
        futs = {ex.submit(probe, r): r for r in rows if r[2] not in existing}
        for f in as_completed(futs):
            try:
                r = f.result(timeout=6)
                if r:
                    rows_to_add.append(r)
            except Exception:
                pass

    if not rows_to_add:
        return 0, Counter()

    # Add to CSV
    tmp = CSV_PATH + ".tmp"
    success = False
    for attempt in range(20):
        try:
            with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
                reader = csv.DictReader(f)
                existing_rows = list(reader)
                header = reader.fieldnames
            start = len(existing_rows) + 1
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            for cid, country, url, ct, server, vtype in rows_to_add:
                new_row = {k: '' for k in header}
                new_row['idx'] = str(start)
                new_row['url'] = url
                new_row['live_stream_url'] = url
                new_row['project_name'] = 'insecam_simple'
                new_row['type'] = vtype
                new_row['enabled'] = '1'
                new_row['live_status'] = 'live'
                new_row['http_status'] = '200'
                new_row['content_type'] = ct
                new_row['server_header'] = server
                new_row['brand'] = 'Insecam'
                new_row['category'] = 'public_cam'
                new_row['country'] = country
                new_row['confidence'] = '0.6'
                new_row['notes'] = f"Insecam simple {ts} | cam_id={cid}"
                new_row['csv_id'] = f"INSECAMSIMPLE-{int(time.time())}-{start}"
                m = re.match(r'https?://([^/]+)', url)
                new_row['host'] = m.group(1) if m else ''
                existing_rows.append(new_row)
                start += 1
            with open(tmp, 'w', encoding='utf-8', newline='') as f:
                w = csv.DictWriter(f, fieldnames=header, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
                w.writeheader()
                w.writerows(existing_rows)
            os.replace(tmp, CSV_PATH)
            success = True
            break
        except PermissionError:
            time.sleep(2 + random.uniform(0, 3))
    if not success:
        return 0, Counter()
    for r in rows_to_add:
        existing.add(r[2])
    types = Counter(r[5] for r in rows_to_add)
    return len(rows_to_add), types


def main():
    csv.field_size_limit(2**31 - 1)
    existing = set()
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            if row.get('url'):
                existing.add(row['url'])
    print(f'  CSV has {len(existing):,} URLs', flush=True)

    # Load progress if any
    progress_file = 'insecam_simple_progress.json'
    done_countries = set()
    if os.path.exists(progress_file):
        with open(progress_file) as f:
            done_countries = set(json.load(f))
    print(f'  Done countries: {len(done_countries)}', flush=True)

    # Country list
    ALL_CC = ['US', 'JP', 'DE', 'IT', 'KR', 'FR', 'GB', 'CA', 'ES', 'MX', 'BR', 'RU',
              'IN', 'CN', 'TW', 'TH', 'VN', 'ID', 'MY', 'PH', 'AU', 'NZ', 'NL', 'BE',
              'PL', 'CZ', 'HU', 'AT', 'CH', 'SE', 'NO', 'FI', 'DK', 'IE', 'PT', 'GR',
              'TR', 'IL', 'AE', 'SA', 'EG', 'ZA', 'NG', 'KE', 'AR', 'CL', 'CO', 'PE',
              'VE', 'EC', 'BO', 'CR', 'PA', 'GT', 'HN', 'NI', 'SV', 'CU', 'DO', 'PR',
              'JM', 'HT', 'TT', 'PK', 'BD', 'LK', 'NP', 'MM', 'KH', 'LA', 'SG',
              'HK', 'MO', 'IR', 'IQ', 'SY', 'LB', 'JO', 'YE', 'OM', 'QA', 'KW', 'BH',
              'AF', 'UZ', 'KZ', 'KG', 'TJ', 'TM', 'AZ', 'AM', 'GE', 'BY', 'UA', 'MD',
              'LV', 'LT', 'EE', 'IS', 'LU', 'MT', 'CY', 'BG', 'RO', 'RS', 'HR', 'SI',
              'BA', 'MK', 'AL', 'ME', 'DZ', 'MA', 'TN', 'LY', 'SD', 'ET', 'TZ',
              'UG', 'ZW', 'ZM', 'MW', 'MZ', 'AO', 'CG', 'GA', 'CM', 'CI', 'GH',
              'SN', 'ML', 'BF', 'NE', 'TD', 'SO', 'RW', 'BI', 'DJ', 'ER', 'SS', 'CF',
              'FJ', 'PG', 'WS', 'TO', 'VU', 'SB', 'KI', 'FM', 'PW', 'MH', 'NR', 'TV',
              'MN', 'BT', 'MV', 'PY', 'UY', 'GY', 'SR', 'GF']

    total_added = 0
    for cc in ALL_CC:
        if cc in done_countries:
            continue
        try:
            t0 = time.time()
            direct = scrape_one_country(cc, max_pages=2)
            n_added, types = probe_and_add(direct, existing)
            elapsed = time.time() - t0
            total_added += n_added
            print(f'  {cc}: {len(direct)} found, {n_added} added ({elapsed:.1f}s) types={dict(types)}', flush=True)
            done_countries.add(cc)
            with open(progress_file, 'w') as f:
                json.dump(sorted(done_countries), f)
        except Exception as e:
            print(f'  {cc}: ERR {e}', flush=True)
        time.sleep(0.5)

    print(f'\n[FINAL] Total added: {total_added}')


if __name__ == '__main__':
    main()
