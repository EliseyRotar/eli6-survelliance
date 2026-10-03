"""Run insecam scrape + add in a loop, exhaustively covering all countries.

Continues until all countries are done.
"""
import csv
import os
import time
import json
import re
import urllib.request
import ssl
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

import glob

CSV_PATH = None
for f in glob.glob(r'C:\Users\eli6-admin\Documents\**/controllable_Webcams.csv', recursive=True):
    CSV_PATH = f
    break
if not CSV_PATH:
    print('CSV not found')
    exit(1)
print(f'CSV: {CSV_PATH}')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def fetch(url, timeout=8):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, r.headers.get('Content-Type', ''), r.read()
    except urllib.error.HTTPError as e:
        return e.code, '', b''
    except Exception as e:
        return -1, str(e)[:100], b''


# Top 60 countries by cam count (most popular residential cam countries)
ALL_CC = [
    'US', 'JP', 'DE', 'IT', 'KR', 'FR', 'GB', 'CA', 'ES', 'MX', 'BR', 'RU',
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
    'MN', 'BT', 'MV', 'CO', 'VE', 'EC', 'PA', 'PY', 'UY', 'GY', 'SR', 'GF',
    'FK', 'BS', 'BB', 'GD', 'LC', 'VC', 'DM', 'KN', 'AG', 'TC', 'KY', 'BM',
    'VG', 'VI', 'PR', 'AW', 'CW', 'SX', 'BQ', 'MF', 'BL', 'PM', 'GL', 'FO',
    'GI', 'JE', 'GG', 'IM', 'AX', 'LI', 'MC', 'AD', 'SM', 'VA',
]


def scrape_country(cc, max_pages=3):
    out = []
    for page in range(1, max_pages + 1):
        url = f'https://www.insecam.org/en/bycountry/{cc}/?page={page}'
        status, ct, body = fetch(url, timeout=8)
        if status != 200:
            break
        try:
            html = body.decode('utf-8', errors='replace')
        except:
            break
        cams = []
        for m in re.finditer(r'href="(/en/view/(\d+)/?)"', html):
            cam_id = m.group(2)
            cams.append({
                'id': cam_id,
                'url': f'https://www.insecam.org/en/view/{cam_id}/',
                'country': cc,
            })
        out.extend(cams)
        if not cams:
            break
        time.sleep(0.2)
    return out


def get_direct_url(cam_id, timeout=5):
    url = f'https://www.insecam.org/en/view/{cam_id}/'
    status, ct, body = fetch(url, timeout=timeout)
    if status != 200:
        return None, None
    try:
        html = body.decode('utf-8', errors='replace')
    except:
        return None, None
    m = re.search(r'<img[^>]+id="image0"[^>]+src="([^"]+)"', html)
    if not m:
        m = re.search(r'<img[^>]+src="(https?://[^"]+\.jpg)"', html)
    if m:
        return m.group(1), html
    return None, None


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


def probe_stream(url, timeout=4, max_bytes=512*1024):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            data = r.read(max_bytes)
            ct = r.headers.get('Content-Type', '')
            return r.status, ct, len(data), r.headers.get('Server', '')
    except urllib.error.HTTPError as e:
        return e.code, '', 0, ''
    except Exception as e:
        return -1, str(e)[:50], 0, ''


def save_to_csv(rows):
    """Save rows to CSV with lock retry."""
    tmp = CSV_PATH + ".tmp"
    for attempt in range(20):
        try:
            with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
                reader = csv.DictReader(f)
                existing_rows = list(reader)
                header = reader.fieldnames
            start = len(existing_rows) + 1
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            for r in rows:
                new_row = {k: '' for k in header}
                new_row['idx'] = str(start)
                new_row['url'] = r['url']
                new_row['live_stream_url'] = r['url']
                new_row['project_name'] = 'insecam_v3'
                new_row['type'] = r['type']
                new_row['enabled'] = '1'
                new_row['live_status'] = 'live'
                new_row['http_status'] = '200'
                new_row['content_type'] = r['ct']
                new_row['server_header'] = r['server']
                new_row['brand'] = 'Insecam'
                new_row['category'] = 'public_cam'
                new_row['country'] = r['country']
                new_row['confidence'] = '0.6'
                new_row['notes'] = f"Insecam country V3 {ts} | cam_id={r['id']}"
                new_row['csv_id'] = f"INSECAMV3-{int(time.time())}-{start}"
                m = re.match(r'https?://([^/]+)', r['url'])
                new_row['host'] = m.group(1) if m else ''
                existing_rows.append(new_row)
                start += 1
            with open(tmp, 'w', encoding='utf-8', newline='') as f:
                w = csv.DictWriter(f, fieldnames=header, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
                w.writeheader()
                w.writerows(existing_rows)
            os.replace(tmp, CSV_PATH)
            return True
        except PermissionError:
            time.sleep(2 + random.uniform(0, 3))
    return False


def main():
    # Load existing URLs
    csv.field_size_limit(2**31 - 1)
    existing = set()
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            if row.get('url'):
                existing.add(row['url'])
    print(f'  CSV has {len(existing):,} URLs')

    random.seed(456)

    # Process countries in batches
    total_added = 0
    total_processed = 0
    BATCH = 10  # countries per batch
    for batch_start in range(0, len(ALL_CC), BATCH):
        batch_ccs = ALL_CC[batch_start:batch_start + BATCH]
        print(f'\n[Batch {batch_start//BATCH + 1}] Countries: {",".join(batch_ccs)}')

        # Step 1: Get cam IDs
        all_cams = []
        with ThreadPoolExecutor(max_workers=10) as ex:
            futs = {ex.submit(scrape_country, cc): cc for cc in batch_ccs}
            for f in as_completed(futs):
                try:
                    cams = f.result(timeout=60)
                    all_cams.extend(cams)
                except Exception:
                    pass

        # Step 2: Get direct URLs
        direct_urls = []
        with ThreadPoolExecutor(max_workers=20) as ex:
            def visit(cam):
                d, _ = get_direct_url(cam['id'])
                if d:
                    return {**cam, 'direct': d}
                return None
            futs = {ex.submit(visit, c): c for c in all_cams}
            for f in as_completed(futs):
                try:
                    r = f.result(timeout=10)
                    if r:
                        direct_urls.append(r)
                except Exception:
                    pass

        # Step 3: Filter new + probe
        new = [r for r in direct_urls if r['direct'] not in existing]
        print(f'  {len(direct_urls)} URLs found, {len(new)} new')

        rows_to_add = []
        with ThreadPoolExecutor(max_workers=30) as ex:
            def probe(r):
                u = r['direct']
                status, ct, size, server = probe_stream(u, timeout=4)
                if status == 200:
                    video_type = detect_video_type(u, ct)
                    return {
                        'id': r['id'],
                        'url': u,
                        'ct': ct,
                        'type': video_type,
                        'server': server,
                        'country': r['country'],
                    }
                return None
            futs = {ex.submit(probe, r): r for r in new}
            for f in as_completed(futs):
                try:
                    r = f.result(timeout=8)
                    if r:
                        rows_to_add.append(r)
                except Exception:
                    pass

        # Step 4: Add to CSV
        if rows_to_add:
            success = save_to_csv(rows_to_add)
            if success:
                # Update existing set
                for r in rows_to_add:
                    existing.add(r['url'])
                total_added += len(rows_to_add)
                types = Counter(r['type'] for r in rows_to_add)
                print(f'  Added {len(rows_to_add)} cams: {dict(types)}')
            else:
                print(f'  ERROR: could not write CSV')

        total_processed += len(new)
        if total_processed % 100 == 0:
            print(f'\n[Stats] Total processed: {total_processed}, Total added: {total_added}')
        time.sleep(1)

    print(f'\n[FINAL] Total added: {total_added} cams')


if __name__ == '__main__':
    main()
