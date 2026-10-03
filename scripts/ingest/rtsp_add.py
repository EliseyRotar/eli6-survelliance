"""Add RTSP streams to CSV and proxy them via rtsp_mjpeg_proxy."""
import csv
import os
import time
import json
import re
import random

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
    # Load RTSP results
    if os.path.exists('rtsp_full_results_v2.json'):
        with open('rtsp_full_results_v2.json', 'r') as f:
            v2 = json.load(f)
        # v2 format: [ip, path, creds, body]
        results = []
        for ip, path, creds, body in v2:
            results.append((ip, path, '', creds, '200', body))
    elif os.path.exists('rtsp_full_results.json'):
        with open('rtsp_full_results.json', 'r') as f:
            results = json.load(f)
    else:
        print('  No RTSP results file')
        return
    print(f'  Loaded {len(results)} RTSP results')

    # Build RTSP URLs
    new_rows = []
    seen_urls = set()
    for item in results:
        if len(item) == 6:
            ip, path, pname, creds, status, body = item
        elif len(item) == 4:
            ip, path, creds, body = item
            pname = path
            status = '200'
        else:
            continue
        if creds:
            rtsp_url = f'rtsp://{creds}@{ip}:554{path}'
        else:
            rtsp_url = f'rtsp://{ip}:554{path}'
        if rtsp_url in seen_urls:
            continue
        seen_urls.add(rtsp_url)

        # Convert to MJPEG proxy URL (will be added when proxy restarts)
        mjpeg_url = f'http://localhost:8768/stream/{ip.replace(".", "_")}'

        new_rows.append({
            'idx': '',
            'url': rtsp_url,
            'live_stream_url': mjpeg_url,
            'project_name': 'rtsp_bulk_discovery',
            'type': 'video-h264-rtsp',
            'enabled': '1',
            'live_status': 'live',
            'http_status': '200',
            'content_type': 'application/sdp',
            'server_header': '',
            'page_title': '',
            'description': f'RTSP stream at {rtsp_url} ({pname})',
            'category': 'public_cam',
            'likely_subject': 'unknown',
            'brand': 'Unknown',
            'model': pname,
            'country': '',
            'region': '',
            'city': '',
            'zip': '',
            'address': '',
            'lat': '',
            'lon': '',
            'geo_source': '',
            'isp': '',
            'org': '',
            'asn': '',
            'reverse_dns': '',
            'host': ip,
            'confidence': '0.7',
            'notes': f'RTSP bulk scan {time.strftime("%Y-%m-%d %H:%M:%S")} | path={pname} | {creds or "no-auth"}',
            'csv_id': f'RTSPBULK-{int(time.time())}-{ip.replace(".", "")}',
        })

    # Filter against existing
    csv.field_size_limit(2**31 - 1)
    existing = set()
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            if row.get('url'):
                existing.add(row['url'])
    print(f'  CSV has {len(existing):,} URLs')

    new_rows = [r for r in new_rows if r['url'] not in existing]
    print(f'  New RTSP rows: {len(new_rows)}')

    if not new_rows:
        return

    # Save atomically with retry
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        reader = csv.DictReader(f)
        existing_rows = list(reader)
        header = reader.fieldnames

    start = len(existing_rows) + 1
    for r in new_rows:
        r['idx'] = str(start)
        start += 1
        existing_rows.append(r)

    tmp = CSV_PATH + ".tmp"
    success = False
    for attempt in range(20):
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
        print(f'  Added {len(new_rows)} RTSP rows to CSV')
    else:
        print('  ERROR: could not write CSV')

    # Save RTSP results for proxy
    proxy_data = {}
    for r in new_rows:
        ip = r['host']
        path = re.search(r':554(/.*)', r['url']).group(1)
        creds = ''
        m = re.search(r'rtsp://([^@]+)@', r['url'])
        if m:
            creds = m.group(1)
        proxy_data[f'{ip}_554{path.replace("/", "_")}'] = {
            'url': r['url'],
            'ip': ip,
            'port': 554,
            'path': path,
            'creds': creds,
        }
    with open('rtsp_proxy_streams.json', 'w') as f:
        json.dump(proxy_data, f, indent=2)
    print(f'  Saved proxy config to rtsp_proxy_streams.json')


if __name__ == '__main__':
    main()
