"""Restore Ruse cams from hardcoded list - the dossier is gone."""
import os
import csv
import re
import json
import time
import random
import socket
import urllib.request
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed

# Auto-find CSV
import glob
CSV_PATH = None
for f in glob.glob(r'C:\Users\eli6-admin\Documents\**/controllable_Webcams.csv', recursive=True):
    CSV_PATH = f
    break

if not CSV_PATH:
    print('CSV not found')
    exit(1)
print(f'CSV: {CSV_PATH}')

# Known Ruse cams (from our prior discoveries)
RUSE_CAMS = [
    # Windy.com cams (Bulgaria region)
    ('https://images-webcams.windy.com/15/1597690315/current/full/1597690315.jpg',
     'ruse_windy', 'Ruse BG - Windy cam 1597690315'),
    ('https://images-webcams.windy.com/15/1793898215/current/full/1793898215.jpg',
     'ruse_windy', 'Ruse BG - Windy cam 1793898215'),
    ('https://images-webcams.windy.com/97/1793902097/current/full/1793902097.jpg',
     'ruse_windy', 'Ruse BG - Windy cam 1793902097'),
    # Yandex weather cam 20758
    ('https://info.weather.yandex.net/20758/3.png', 'ruse_yandex', 'Ruse Yandex weather cam ID 20758'),
    # Worldcam.pl cams (Bulgaria region)
    ('https://www.img.worldcam.pl/webcams/200x113/2026-08-25/14906.jpg', 'ruse_worldcam', 'Ruse - Worldcam cam 14906'),
    ('https://www.img.worldcam.pl/webcams/200x113/2026-08-25/24496.jpg', 'ruse_worldcam', 'Ruse - Worldcam cam 24496'),
    ('https://www.img.worldcam.pl/webcams/200x113/2026-08-25/2706.jpg', 'ruse_worldcam', 'Ruse - Worldcam cam 2706'),
    ('https://www.img.worldcam.pl/webcams/200x113/2026-08-25/37360.jpg', 'ruse_worldcam', 'Ruse - Worldcam cam 37360'),
    ('https://www.img.worldcam.pl/webcams/200x113/2026-08-25/40580.jpg', 'ruse_worldcam', 'Ruse - Worldcam cam 40580'),
    # WebcamsBG street cam
    ('https://webcamsbg.com/cams/ruse-street.jpg', 'ruse_webcamsbg', 'Ruse street cam from webcamsbg.com'),
    # Webcamera24 (auth-required)
    ('https://cdn.webcamera24.com/static/image/camera/detail/8438-omv-bala-uastreaming/',
     'ruse_webcamera24', 'OMV Bala streaming (Ruse area)'),
    ('https://cdn.webcamera24.com/static/image/camera/detail/8565-ueb-kamera-ot-letise-ruse-s-srklevo-uast/',
     'ruse_webcamera24', 'Ruse letishte Srklevo (Ruse airport)'),
    ('https://cdn.webcamera24.com/static/image/camera/detail/8566-ueb-kamera-ot-letise-ruse-lbrs-ruse-do-s/',
     'ruse_webcamera24', 'LBRS Ruse (school)'),
    # Ruse Traffic cam - geofenced BG-only
    ('http://212.25.48.117:8080/axis-cgi/mjpg/video.cgi?webcam.jpg',
     'ruse_axis_geofenced', 'Ruse Traffic cam on 212.25.48.117:8080 - GEOFENCED (BG-only IP)'),
]


def probe_url(url, timeout=8):
    """Probe URL."""
    try:
        ctx = None
        if url.startswith('https://'):
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        ctx_arg = {'context': ctx} if ctx else {}
        with urllib.request.urlopen(req, timeout=timeout, **ctx_arg) as r:
            data = r.read()
            return (r.status, r.headers.get('Content-Type', ''), len(data))
    except urllib.error.HTTPError as e:
        return (e.code, '', 0)
    except Exception as e:
        return (-1, str(e)[:50], 0)


def main():
    print(f'[Ruse Restore V2] Restoring {len(RUSE_CAMS)} Ruse cams')

    csv.field_size_limit(2**31 - 1)

    existing = set()
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row.get('url'):
                existing.add(row['url'])
    print(f'  CSV has {len(existing):,} URLs')

    # Probe and add
    rows_to_add = []
    for url, brand, notes in RUSE_CAMS:
        if url in existing:
            print(f'  [skip] {url[:80]} (already in CSV)')
            continue
        status, ct, size = probe_url(url, timeout=8)
        print(f'  [{status}] {url[:80]} ({ct[:30]}, {size}B)')
        if status == 200:
            live_status = 'live'
        elif status in (401, 403):
            live_status = 'auth_required'
        elif status in (404, 410):
            continue
        elif status == -1:
            live_status = 'auth_required'  # Geofenced
        else:
            live_status = 'unknown'
        rows_to_add.append({
            'url': url,
            'brand': brand,
            'live_status': live_status,
            'http_status': status,
            'content_type': ct,
            'notes': notes,
        })

    if not rows_to_add:
        print('\n[Ruse Restore] Nothing to add')
        return

    # Read current CSV
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        reader = csv.DictReader(f)
        existing_rows = list(reader)
        header = reader.fieldnames

    # Build new rows
    start = len(existing_rows) + 1
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    for cam in rows_to_add:
        new_row = {k: '' for k in header}
        new_row['idx'] = str(start)
        new_row['url'] = cam['url']
        new_row['live_stream_url'] = cam['url']
        new_row['project_name'] = 'ruse_restored'
        new_row['type'] = 'video' if 'mjpg' in cam['url'] else 'image'
        new_row['enabled'] = '1'
        new_row['live_status'] = cam['live_status']
        new_row['http_status'] = str(cam['http_status'])
        new_row['content_type'] = cam['content_type']
        new_row['brand'] = cam['brand']
        new_row['category'] = 'public_cam'
        new_row['country'] = 'Bulgaria'
        new_row['city'] = 'Ruse'
        new_row['lat'] = '43.82306'
        new_row['lon'] = '25.95389'
        new_row['confidence'] = '0.7'
        new_row['notes'] = f"{cam['notes']} | restored {ts}"
        new_row['csv_id'] = f"RUSERESTORED-{int(time.time())}-{start}"
        m = re.match(r'https?://([^/]+)', cam['url'])
        new_row['host'] = m.group(1) if m else ''
        existing_rows.append(new_row)
        start += 1

    # Save atomically with retry on lock
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
    if not success:
        print(f'\n[Ruse Restore] ERROR: Could not write CSV (lock held by another process)')
        return
    print(f'\n[Ruse Restore] Added {len(rows_to_add)} Ruse cams to CSV')

    # Stats
    ruse = [r for r in existing_rows if (r.get('project_name') or '') == 'ruse_restored']
    print(f'  Total Ruse cams now: {len(ruse)}')


if __name__ == '__main__':
    main()
