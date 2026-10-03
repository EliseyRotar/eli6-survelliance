"""Update master CSV rows with RTSP MJPEG proxy URLs."""
import csv
import os
import json
import re
import time
import random
import urllib.request
import ssl

import glob

CSV_PATH = None
for f in glob.glob(r'C:\Users\eli6-admin\Documents\**/controllable_Webcams.csv', recursive=True):
    CSV_PATH = f
    break
if not CSV_PATH:
    print('CSV not found')
    exit(1)
print(f'CSV: {CSV_PATH}')


def main():
    # Get list of fresh streams from proxy
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        r = urllib.request.urlopen('http://localhost:8768/list', timeout=10)
        streams = json.loads(r.read().decode())
    except Exception as e:
        print(f'  Err fetching proxy list: {e}')
        return
    print(f'  Proxy has {len(streams)} streams, {sum(1 for s in streams if s["fresh"])} fresh')

    # Build map: IP -> MJPEG URL
    ip_to_mjpeg = {}
    for s in streams:
        if not s.get('fresh'):
            continue
        m = re.search(r'(\d+\.\d+\.\d+\.\d+)', s.get('url', ''))
        if not m:
            continue
        ip = m.group(1)
        ip_to_mjpeg[ip] = f'http://localhost:8768/stream/{s["id"]}'

    print(f'  Fresh IPs to update: {len(ip_to_mjpeg)}')

    # Read CSV
    csv.field_size_limit(2**31 - 1)
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        header = reader.fieldnames

    # Update rows
    n_updated = 0
    for row in rows:
        url = row.get('url', '') or ''
        if not url.startswith('rtsp://'):
            continue
        m = re.search(r'rtsp://(?:[^@]+@)?(\d+\.\d+\.\d+\.\d+):\d+', url)
        if not m:
            continue
        ip = m.group(1)
        if ip in ip_to_mjpeg:
            new_url = ip_to_mjpeg[ip]
            if (row.get('live_stream_url') or '') != new_url:
                row['live_stream_url'] = new_url
                row['type'] = 'video-mjpeg'
                row['notes'] = (row.get('notes') or '') + f' | MJPEG proxy via RTSP'
                n_updated += 1

    print(f'  Rows updated: {n_updated}')

    if n_updated == 0:
        print('  Nothing to update')
        return

    # Save with retry
    tmp = CSV_PATH + ".tmp"
    for attempt in range(20):
        try:
            with open(tmp, 'w', encoding='utf-8', newline='') as f:
                w = csv.DictWriter(f, fieldnames=header, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
                w.writeheader()
                w.writerows(rows)
            os.replace(tmp, CSV_PATH)
            print(f'  Saved CSV with {n_updated} updated rows')
            return
        except PermissionError:
            time.sleep(2 + random.uniform(0, 3))
    print('  ERROR: Could not save CSV')


if __name__ == '__main__':
    main()
