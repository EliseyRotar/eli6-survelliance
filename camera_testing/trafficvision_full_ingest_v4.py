"""Ingest the 2,848 missing TV cams with the v3 ingestor but with all sources accepted.

This v4 ingests cams even if they only have a sourceUrl (no direct video/image).
"""
import csv
import json
import os
import re
import sys
import time
import random

sys.stdout.reconfigure(line_buffering=True)

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\trafficvision_v4_log.txt'
PROGRESS_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\trafficvision_v4_progress.json'
MISSING_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\tv_missing.json'

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
    """Build CSV row from TV catalog cam record. Always returns a row, using any URL we can find."""
    cam_id = rec.get('id', '')
    if not cam_id:
        return None
    src = rec.get('source', '') or 'tv'
    full_id = f'{src}:{cam_id}'

    # Get any URL
    video_url = rec.get('videoUrl', '') or ''
    image_url = rec.get('imageUrl', '') or ''
    player_url = rec.get('playerUrl', '') or ''
    youtube_id = rec.get('youtubeVideoId', '') or ''
    ipcam_alias = rec.get('ipcamliveAlias', '') or ''
    source_url = rec.get('sourceUrl', '') or ''
    go2rtc = rec.get('go2rtcWsUrl', '') or ''

    # Check angles
    angles = rec.get('angles') or []
    if not video_url and angles:
        for ang in angles:
            if isinstance(ang, dict):
                v = ang.get('videoUrl') or ''
                i = ang.get('imageUrl') or ''
                if v:
                    video_url = v
                    break
                if i and not image_url:
                    image_url = i

    # Pick URL
    if video_url:
        live_url = video_url
    elif player_url:
        live_url = player_url
    elif youtube_id:
        live_url = f'https://www.youtube.com/watch?v={youtube_id}'
    elif ipcam_alias:
        live_url = f'https://ipcamlive.com/{ipcam_alias}'
    elif image_url:
        live_url = image_url
    elif go2rtc:
        live_url = go2rtc
    elif source_url:
        live_url = source_url
    else:
        return None

    m = re.match(r'(?:https?|rtsp|rtmp)://([^/:]+)', live_url)
    host = m.group(1) if m else ''
    if host.startswith('www.'):
        host = host[4:]

    location = rec.get('location', '')
    city = rec.get('city', '')
    state = rec.get('state', '')
    roadway = rec.get('roadway', '')
    direction = rec.get('direction', '')
    description = rec.get('description', '')
    name = rec.get('name', '') or location
    if not name:
        parts = [p for p in [roadway, direction, city] if p]
        name = ' - '.join(parts) if parts else f'{host} cam'
    name = name.replace('\u2013', '-').replace('\u2014', '-')

    lu = live_url.lower()
    if 'm3u8' in lu:
        ctype = 'application/vnd.apple.mpegurl'
    elif 'mp4' in lu:
        ctype = 'video/mp4'
    elif 'mjpeg' in lu or 'mjpg' in lu:
        ctype = 'multipart/x-mixed-replace'
    elif 'youtube' in lu or 'youtu.be' in lu:
        ctype = 'text/html'
    else:
        ctype = 'image/jpeg'

    lat = str(rec.get('lat', ''))
    lon = str(rec.get('lng', ''))
    country = rec.get('country', '')
    region = rec.get('state', '') or ''
    if isinstance(region, dict):
        region = ''
    cat = rec.get('category', '') or (rec.get('categories', [''])[0] if rec.get('categories') else '')
    county = rec.get('county', '')
    postcode = rec.get('postcode', '')
    road = rec.get('road', '')
    feed_type = rec.get('feedType', '')
    make = rec.get('make', '')
    model = rec.get('model', '')

    notes_parts = [f'trafficvision_id={full_id}']
    if make: notes_parts.append(f'make={make}')
    if model: notes_parts.append(f'model={model}')
    if county: notes_parts.append(f'county={county}')
    if roadway: notes_parts.append(f'roadway={roadway}')
    if feed_type: notes_parts.append(f'feedType={feed_type}')
    notes = '; '.join(notes_parts)

    if 'm3u8' in lu or 'mp4' in lu or 'mjpeg' in lu or 'mjpg' in lu or 'ipcamlive' in lu or 'youtube' in lu:
        rtype = 'video'
    else:
        rtype = 'image'

    out = {h: '' for h in header}
    out['project_name'] = name[:100]
    out['url'] = live_url
    out['live_stream_url'] = live_url
    out['type'] = rtype
    out['enabled'] = '1'
    out['live_status'] = 'live'
    out['http_status'] = '200'
    out['content_type'] = ctype
    out['description'] = description[:200]
    out['category'] = cat or 'public'
    out['likely_subject'] = 'Live public camera'
    out['brand'] = make
    out['model'] = model
    out['country'] = country
    out['region'] = region
    out['city'] = city
    out['zip'] = postcode
    out['lat'] = lat
    out['lon'] = lon
    out['geo_source'] = 'trafficvision.live'
    out['org'] = f'TrafficVision ({src})'
    out['host'] = host
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
        log('  WARN: could not acquire lock')
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
            r['csv_id'] = f'tv4_{next_idx:04d}'
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
    log('[init] TV ingest v4 - filling missing cams')
    if not os.path.exists(MISSING_PATH):
        log(f'ERROR: {MISSING_PATH} not found')
        sys.exit(1)
    with open(MISSING_PATH) as f:
        missing = json.load(f)
    log(f'  loaded {len(missing):,} missing cams')

    header = get_header()
    seen_urls, seen_ids = load_existing()
    log(f'  existing: {len(seen_urls):,} URLs, {len(seen_ids):,} TV IDs')

    batch = []
    added = 0
    skipped = 0
    t0 = time.time()

    for i, rec in enumerate(missing):
        try:
            result = build_row(rec, header)
        except Exception as e:
            log(f'  build_row err at {i}: {e}')
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
            rate = added / max(elapsed, 1)
            log(f'  {i+1}/{len(missing)} processed, {added} added, {skipped} skipped, {rate:.0f}/s')

    # Flush remaining
    if batch:
        n = append_batch(batch, header)
        added += n

    elapsed = time.time() - t0
    rate = added / max(elapsed, 1)
    log(f'\n[done] added {added}, skipped {skipped}, in {elapsed:.1f}s ({rate:.0f}/s)')


if __name__ == '__main__':
    main()
