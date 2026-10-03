"""Filter scraped URLs for actual cam URLs, then add to CSV.

Useful URL patterns:
- /webcam/ paths
- /cam/ paths
- /image.jpg
- /online/wp-content/uploads (WordPress cam images)
- /livestream/
"""
import json
import csv
import re
import os
import sys
import time
import random

sys.stdout.reconfigure(line_buffering=True)

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
SCRAPE_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\tv_missing_scrape.json'
MISSING_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\tv_missing.json'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\trafficvision_v4d_log.txt'

BATCH_SIZE = 500
csv.field_size_limit(2**31 - 1)


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def is_useful_url(url):
    """Check if URL is a useful cam URL (not favicon, not social media)."""
    url_lower = url.lower()
    # Skip favicons and social media
    bad_patterns = [
        'favicon', 'logo', 'social', 'wp-content/themes', 'wp-includes',
        'facebook', 'twitter', 'youtube.com/watch', 'icon', 'avatar',
        'wp-content/plugins', 'screenshot',
    ]
    for p in bad_patterns:
        if p in url_lower:
            return False
    # Must be image-like
    if not (url_lower.endswith('.jpg') or url_lower.endswith('.jpeg') or url_lower.endswith('.png')):
        return False
    return True


def get_header():
    return ['idx', 'project_name', 'url', 'live_stream_url', 'type', 'auth_required', 'auth_user', 'auth_pass', 'enabled', 'live_status', 'http_status', 'content_type', 'server_header', 'page_title', 'description', 'category', 'likely_subject', 'brand', 'model', 'country', 'region', 'city', 'zip', 'address', 'lat', 'lon', 'geo_source', 'isp', 'org', 'asn', 'reverse_dns', 'host', 'confidence', 'notes', 'csv_id']


def build_row(url, source, src_url, header):
    m = re.match(r'https?://(?:www\.)?([^/]+)', url)
    host = m.group(1) if m else ''

    # Derive a name from the URL
    path = url.split('/', 3)[-1] if '/' in url else url
    name = path.replace('.jpg', '').replace('.jpeg', '').replace('.png', '').replace('-', ' ').replace('_', ' ').title()[:80]

    out = {h: '' for h in header}
    out['project_name'] = f'{source} {name}'[:100]
    out['url'] = url
    out['live_stream_url'] = url
    out['type'] = 'image'
    out['enabled'] = '1'
    out['live_status'] = 'live'
    out['http_status'] = '200'
    out['content_type'] = 'image/jpeg' if url.lower().endswith(('.jpg', '.jpeg')) else 'image/png'
    out['category'] = 'public'
    out['likely_subject'] = 'Live public camera'
    out['brand'] = source
    out['country'] = ''
    out['geo_source'] = 'trafficvision.live'
    out['org'] = f'TrafficVision ({source})'
    out['host'] = host
    out['confidence'] = '0.6'
    out['notes'] = f'trafficvision_missing_scrape | {src_url}'
    return out, host


def load_existing():
    seen_urls = set()
    seen_hosts = set()
    if not os.path.exists(CSV_PATH):
        return seen_urls, seen_hosts
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        rows = list(csv.reader(f))
    for row in rows[1:]:
        if len(row) > 3 and row[3]:
            seen_urls.add(row[3].lower().strip())
        if len(row) > 31 and row[31]:
            seen_hosts.add(row[31].lower().strip())
    return seen_urls, seen_hosts


def append_batch(rows_out, header):
    if not rows_out:
        return 0
    valid_rows = []
    for r in rows_out:
        if not r.get('live_stream_url') or not r.get('project_name'):
            continue
        valid_rows.append(r)
    if not valid_rows:
        return 0
    rows_out = valid_rows
    lock_path = CSV_PATH + '.lock'
    lock_fd = None
    for attempt in range(120):
        try:
            lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            break
        except FileExistsError:
            time.sleep(0.05 + 0.02 * (attempt % 10))
    if lock_fd is None:
        return 0
    try:
        with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
            existing = list(csv.reader(f))
        max_idx = 0
        for r in existing[1:]:
            try:
                if r and r[0]:
                    max_idx = max(max_idx, int(r[0]))
            except Exception:
                pass
        next_idx = max_idx + 1
        for r in rows_out:
            r['idx'] = str(next_idx)
            r['csv_id'] = f'tv4d_{next_idx:04d}'
            next_idx += 1
        tmp_path = CSV_PATH + '.tmp'
        with open(tmp_path, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
            w.writerow(header)
            for r in existing[1:]:
                if r and len(r) >= len(header):
                    w.writerow(r)
            for r in rows_out:
                row_list = [str(r.get(h, '')).replace('\r', ' ').replace('\n', ' ') for h in header]
                w.writerow(row_list)
        for _ in range(20):
            try:
                os.replace(tmp_path, CSV_PATH)
                return len(rows_out)
            except PermissionError:
                time.sleep(0.3)
        return 0
    finally:
        if lock_fd is not None:
            try: os.close(lock_fd)
            except: pass
            try: os.unlink(lock_path)
            except OSError: pass


def main():
    log('[init] TV v4d - ingest scraped URLs from missing cam landing pages')

    if not os.path.exists(SCRAPE_PATH):
        log(f'ERROR: {SCRAPE_PATH} not found')
        sys.exit(1)

    with open(SCRAPE_PATH) as f:
        scraped = json.load(f)
    log(f'  loaded scraped URLs from {len(scraped)} sources')

    # Filter to useful URLs
    useful = []
    for src_url, urls in scraped.items():
        for u in urls:
            if is_useful_url(u):
                # Derive source name
                m = re.match(r'https?://(?:www\.)?([^/]+)', src_url)
                src_name = m.group(1) if m else 'unknown'
                useful.append((u, src_name, src_url))
    log(f'  {len(useful):,} useful URLs after filtering')

    # Dedupe
    seen = set()
    unique_useful = []
    for u, s, src in useful:
        if u not in seen:
            seen.add(u)
            unique_useful.append((u, s, src))
    log(f'  {len(unique_useful):,} unique useful URLs')

    header = get_header()
    seen_urls, seen_hosts = load_existing()
    log(f'  existing: {len(seen_urls):,} URLs')

    batch = []
    added = 0
    skipped = 0
    t0 = time.time()

    for url, source, src_url in unique_useful:
        if url.lower() in seen_urls:
            skipped += 1
            continue
        seen_urls.add(url.lower())
        result = build_row(url, source, src_url, header)
        if result is None:
            skipped += 1
            continue
        row_dict, host = result
        batch.append(row_dict)
        if len(batch) >= BATCH_SIZE:
            n = append_batch(batch, header)
            added += n
            batch = []
            elapsed = time.time() - t0
            log(f'  {added} added, {skipped} skipped, {elapsed:.0f}s')

    if batch:
        n = append_batch(batch, header)
        added += n

    log(f'\n[done] added {added}, skipped {skipped}, in {time.time()-t0:.1f}s')


if __name__ == '__main__':
    main()
