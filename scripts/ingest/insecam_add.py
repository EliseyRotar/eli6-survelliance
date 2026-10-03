"""Probe insecam country results and add to master CSV."""
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


def fetch(url, timeout=5, max_bytes=1024*1024):
    """Read just first 1MB to determine type without downloading entire stream."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            data = r.read(max_bytes)
            return r.status, r.headers.get('Content-Type', ''), len(data), r.headers
    except urllib.error.HTTPError as e:
        return e.code, '', 0, {}
    except Exception as e:
        return -1, str(e)[:100], 0, {}


def detect_video_type(url, content_type, headers):
    """Detect if URL is a video stream and what type."""
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


def main():
    # Load existing
    csv.field_size_limit(2**31 - 1)
    existing = set()
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            if row.get('url'):
                existing.add(row['url'])
    print(f'  CSV has {len(existing):,} URLs')

    # Load insecam results
    with open('insecam_country_results.json', 'r', encoding='utf-8') as f:
        results = json.load(f)
    print(f'  Loaded {len(results)} insecam results')

    # Filter new
    new = [r for r in results if r['direct'] not in existing]
    print(f'  New (not in CSV): {len(new)}')

    # Probe each
    print(f'\n[Probe] Probing {len(new)} URLs...')
    probed = []
    with ThreadPoolExecutor(max_workers=30) as ex:
        def probe_one(r):
            url = r['direct']
            status, ct, size, headers = fetch(url, timeout=4, max_bytes=512*1024)
            video_type = detect_video_type(url, ct, headers)
            return {
                **r,
                'status': status,
                'ct': ct,
                'size': size,
                'video_type': video_type,
                'server': headers.get('Server', ''),
            }

        futs = {ex.submit(probe_one, r): r for r in new}
        n_done = 0
        for f in as_completed(futs):
            try:
                r = f.result(timeout=8)
                if r and r['status'] == 200:
                    probed.append(r)
            except Exception as e:
                pass
            n_done += 1
            if n_done % 30 == 0:
                live = len([p for p in probed if p.get('status') == 200])
                print(f'  {n_done}/{len(new)} probed, {live} live', flush=True)

    print(f'\n  Total live: {len(probed)}')

    # Count video types
    types = Counter(p['video_type'] for p in probed)
    print(f'\nVideo types:')
    for t, c in types.most_common():
        print(f'  {t}: {c}')

    # Add to CSV
    if not probed:
        print('\nNothing to add')
        return

    print(f'\n[Add] Adding {len(probed)} to CSV...')
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        reader = csv.DictReader(f)
        existing_rows = list(reader)
        header = reader.fieldnames

    start = len(existing_rows) + 1
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    n_added = 0
    for p in probed:
        new_row = {k: '' for k in header}
        new_row['idx'] = str(start)
        new_row['url'] = p['direct']
        new_row['live_stream_url'] = p['direct']
        new_row['project_name'] = 'insecam_country'
        new_row['type'] = p['video_type']
        new_row['enabled'] = '1'
        new_row['live_status'] = 'live'
        new_row['http_status'] = '200'
        new_row['content_type'] = p['ct']
        new_row['server_header'] = p['server']
        new_row['page_title'] = p.get('title', '')
        new_row['brand'] = 'Insecam'
        new_row['category'] = 'public_cam'
        new_row['country'] = p.get('country', '')
        new_row['confidence'] = '0.6'
        new_row['notes'] = f"Insecam country scrape {ts} | cam_id={p.get('id', '')}"
        new_row['csv_id'] = f"INSECAMCTRY-{int(time.time())}-{start}"
        m = re.match(r'https?://([^/]+)', p['direct'])
        new_row['host'] = m.group(1) if m else ''
        existing_rows.append(new_row)
        start += 1
        n_added += 1

    # Save with retry
    tmp = CSV_PATH + ".tmp"
    success = False
    for attempt in range(15):
        try:
            with open(tmp, 'w', encoding='utf-8', newline='') as f:
                w = csv.DictWriter(f, fieldnames=header, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
                w.writeheader()
                w.writerows(existing_rows)
            os.replace(tmp, CSV_PATH)
            success = True
            break
        except PermissionError:
            time.sleep(2 + random.uniform(0, 3))

    if success:
        print(f'  Added {n_added} cams to CSV')
    else:
        print(f'  ERROR: Could not write CSV')


if __name__ == '__main__':
    main()
