"""V4c - ingest YouTube ID missing cams.

These are cams with youtubeVideoId but no direct URL. The v3 missed them
because we filter out generic YouTube channel URLs.
"""
import csv
import json
import os
import re
import sys
import time

sys.stdout.reconfigure(line_buffering=True)

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\trafficvision_v4c_log.txt'
MISSING_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\tv_missing.json'

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


def get_header():
    return ['idx', 'project_name', 'url', 'live_stream_url', 'type', 'auth_required', 'auth_user', 'auth_pass', 'enabled', 'live_status', 'http_status', 'content_type', 'server_header', 'page_title', 'description', 'category', 'likely_subject', 'brand', 'model', 'country', 'region', 'city', 'zip', 'address', 'lat', 'lon', 'geo_source', 'isp', 'org', 'asn', 'reverse_dns', 'host', 'confidence', 'notes', 'csv_id']


def build_row(rec, header):
    cam_id = rec.get('id', '')
    if not cam_id:
        return None
    src = rec.get('source', '') or 'tv'
    full_id = f'{src}:{cam_id}'

    yt = rec.get('youtubeVideoId', '') or ''
    if not yt:
        return None

    live_url = f'https://www.youtube.com/watch?v={yt}'

    location = rec.get('location', '')
    city = rec.get('city', '')
    state = rec.get('state', '')
    roadway = rec.get('roadway', '')
    description = rec.get('description', '')
    name = rec.get('name', '') or location
    if not name:
        name = f'{city} YouTube cam' if city else f'{src} cam'
    name = name.replace('\u2013', '-').replace('\u2014', '-')[:100]

    lat = str(rec.get('lat', ''))
    lon = str(rec.get('lng', ''))
    country = rec.get('country', '')
    region = rec.get('state', '') or ''
    cat = rec.get('category', '') or (rec.get('categories', [''])[0] if rec.get('categories') else '')

    notes = f'trafficvision_id={full_id}; youtube=1'
    if roadway: notes += f'; roadway={roadway}'

    out = {h: '' for h in header}
    out['project_name'] = name
    out['url'] = live_url
    out['live_stream_url'] = live_url
    out['type'] = 'video'
    out['enabled'] = '1'
    out['live_status'] = 'live'
    out['http_status'] = '200'
    out['content_type'] = 'text/html'
    out['description'] = description[:200]
    out['category'] = cat or 'public'
    out['likely_subject'] = 'YouTube live stream'
    out['country'] = country
    out['region'] = region
    out['city'] = city
    out['lat'] = lat
    out['lon'] = lon
    out['geo_source'] = 'trafficvision.live'
    out['org'] = f'TrafficVision ({src})'
    out['host'] = 'youtube.com'
    out['confidence'] = 'high'
    out['notes'] = notes
    return out, full_id, live_url.lower()


def load_existing():
    seen_urls = set()
    seen_ids = set()
    if not os.path.exists(CSV_PATH):
        return seen_urls, seen_ids
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        rows = list(csv.reader(f))
    for row in rows[1:]:
        if len(row) > 3 and row[3]:
            seen_urls.add(row[3].lower().strip())
        if len(row) > 33 and row[33]:
            for m in re.finditer(r'trafficvision_id=([^\s;,]+)', row[33]):
                seen_ids.add(m.group(1))
    return seen_urls, seen_ids


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
            r['csv_id'] = f'tv4c_{next_idx:04d}'
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
    log('[init] TV v4c - YouTube ID missing cams')
    if not os.path.exists(MISSING_PATH):
        log(f'ERROR: {MISSING_PATH} not found')
        sys.exit(1)
    with open(MISSING_PATH) as f:
        missing = json.load(f)

    # Filter to YouTube ID only
    yt_only = [c for c in missing if c.get('youtubeVideoId') and not (c.get('videoUrl') or c.get('imageUrl') or c.get('playerUrl') or c.get('ipcamliveAlias'))]
    log(f'  {len(yt_only):,} YouTube-only missing cams')

    header = get_header()
    seen_urls, seen_ids = load_existing()
    log(f'  existing: {len(seen_urls):,} URLs, {len(seen_ids):,} TV IDs')

    batch = []
    added = 0
    skipped = 0
    t0 = time.time()

    for rec in yt_only:
        try:
            result = build_row(rec, header)
        except Exception:
            continue
        if result is None:
            skipped += 1
            continue
        row_dict, full_id, lower_url = result
        if lower_url in seen_urls or full_id in seen_ids:
            skipped += 1
            continue
        seen_urls.add(lower_url)
        seen_ids.add(full_id)
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
