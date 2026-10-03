"""TV full ingest v3 - fast batched writer, skips duplicates via in-memory set.

Strategy:
1. Load catalog (148,575 cams)
2. Load all existing URLs/IDs into in-memory set
3. Process all cams, building a batch
4. Append batch to CSV atomically (1000 cams at a time)
5. Re-loop on remaining cams

Expected: 1000+ cams/sec batched.
"""
import csv
import json
import os
import re
import sys
import time

sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\trafficvision_full_log.txt'
PROGRESS_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\trafficvision_full_progress.json'
CATALOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_catalog_full.json'

BATCH_SIZE = 1000
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
    """Return the canonical 35-column header (don't read from CSV which may be corrupt)."""
    return ['idx', 'project_name', 'url', 'live_stream_url', 'type', 'auth_required', 'auth_user', 'auth_pass', 'enabled', 'live_status', 'http_status', 'content_type', 'server_header', 'page_title', 'description', 'category', 'likely_subject', 'brand', 'model', 'country', 'region', 'city', 'zip', 'address', 'lat', 'lon', 'geo_source', 'isp', 'org', 'asn', 'reverse_dns', 'host', 'confidence', 'notes', 'csv_id']


def build_row(rec, source_default, header):
    cam_id = rec.get('id', '')
    if not cam_id:
        return None
    full_id = f'{source_default}:{cam_id}' if source_default else cam_id
    # Pick best URL (also check nested angles[] array)
    video_url = rec.get('videoUrl', '') or ''
    image_url = rec.get('imageUrl', '') or ''
    player_url = rec.get('playerUrl', '') or ''
    youtube_id = rec.get('youtubeVideoId', '') or ''
    ipcam_alias = rec.get('ipcamliveAlias', '') or ''
    source_url = rec.get('sourceUrl', '') or ''
    go2rtc = rec.get('go2rtcWsUrl', '') or ''
    # Check angles[] for videoUrl/imageUrl
    angles = rec.get('angles') or []
    if not video_url and angles:
        for ang in angles:
            if isinstance(ang, dict):
                v = ang.get('videoUrl') or ''
                i = ang.get('imageUrl') or ''
                if v and 'm3u8' in v.lower():
                    video_url = v
                    break
                if i and not image_url:
                    image_url = i
    live_url = ''
    if player_url:
        live_url = player_url
    elif video_url and ('m3u8' in video_url or 'mp4' in video_url):
        live_url = video_url
    elif youtube_id:
        live_url = f'https://www.youtube.com/watch?v={youtube_id}'
    elif ipcam_alias:
        live_url = f'https://ipcamlive.com/{ipcam_alias}'
    elif video_url:
        live_url = video_url
    elif image_url:
        live_url = image_url
    elif go2rtc:
        live_url = go2rtc
    elif source_url:
        live_url = source_url
    if not live_url:
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
    source_meta = rec.get('source', '') or source_default
    name = rec.get('name', '') or location
    if not name:
        parts = []
        if roadway:
            parts.append(roadway)
        if direction:
            parts.append(direction)
        if city:
            parts.append(city)
        name = ' - '.join(parts) if parts else f'{host} cam'
    name = name.replace('\u2013', '-').replace('\u2014', '-')

    lu = live_url.lower()
    if 'm3u8' in lu:
        ctype = 'application/vnd.apple.mpegurl'
    elif 'mp4' in lu:
        ctype = 'video/mp4'
    elif 'mjpeg' in lu or 'mjpg' in lu:
        ctype = 'multipart/x-mixed-replace'
    else:
        ctype = 'image/jpeg'

    lat = str(rec.get('lat', ''))
    lon = str(rec.get('lng', ''))
    country = rec.get('country', '')
    region = rec.get('state', '') or rec.get('region', '')
    if isinstance(region, dict):
        region = ''
    cat = rec.get('category', '') or (rec.get('categories', [''])[0] if rec.get('categories') else '')
    make = rec.get('make', '')
    model = rec.get('model', '')
    county = rec.get('county', '')
    postcode = rec.get('postcode', '')
    road = rec.get('road', '')
    display_name = rec.get('display_name', '')
    feed_type = rec.get('feedType', '')

    notes_parts = [f'trafficvision_id={full_id}']
    if make: notes_parts.append(f'make={make}')
    if model: notes_parts.append(f'model={model}')
    if county: notes_parts.append(f'county={county}')
    if roadway: notes_parts.append(f'roadway={roadway}')
    if direction: notes_parts.append(f'dir={direction}')
    if feed_type: notes_parts.append(f'feedType={feed_type}')
    notes = '; '.join(notes_parts)

    if 'm3u8' in lu or 'mp4' in lu or 'mjpeg' in lu or 'mjpg' in lu or 'ipcamlive' in lu or 'youtube' in lu:
        rtype = 'video'
    else:
        rtype = 'image'

    # Return dict indexed by header col name
    out = {h: '' for h in header}
    out['project_name'] = name[:100]
    out['url'] = live_url
    out['live_stream_url'] = live_url
    out['type'] = rtype
    out['auth_required'] = 'False'
    out['enabled'] = 'True'
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
    out['address'] = display_name
    out['lat'] = lat
    out['lon'] = lon
    out['geo_source'] = 'trafficvision.live'
    out['org'] = f'TrafficVision ({source_meta})'
    out['host'] = host
    out['confidence'] = 'high'
    out['notes'] = notes
    return out, full_id, lu


def load_existing():
    seen_urls = set()
    seen_ids = set()
    seen_live = set()
    if not os.path.exists(CSV_PATH):
        return seen_urls, seen_ids, seen_live
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        rows = list(csv.reader(f))
    for row in rows[1:]:
        if len(row) > 3 and row[3]:
            seen_urls.add(row[3].lower().strip())
        if len(row) > 1:
            seen_live.add(row[1])
        if len(row) > 33 and row[33]:
            for m in re.finditer(r'trafficvision_id=([^\s;,]+)', row[33]):
                seen_ids.add(m.group(1))
    return seen_urls, seen_ids, seen_live


def append_batch(rows_out, header):
    """Append rows to CSV atomically. rows_out is list of dicts keyed by header col."""
    if not rows_out:
        return 0
    # Filter out invalid rows
    valid_rows = []
    for r in rows_out:
        # Must have URL and name
        if not r.get('live_stream_url') or not r.get('project_name'):
            continue
        valid_rows.append(r)
    if not valid_rows:
        return 0
    rows_out = valid_rows
    lock_path = CSV_PATH + '.lock'
    import os as _os
    lock_fd = None
    for attempt in range(120):
        try:
            lock_fd = _os.open(lock_path, _os.O_CREAT | _os.O_EXCL | _os.O_RDWR)
            break
        except FileExistsError:
            time.sleep(0.05 + 0.02 * (attempt % 10))
    if lock_fd is None:
        log(f'  WARN: could not acquire lock after 120 attempts')
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
            r['csv_id'] = f'tv_{next_idx:04d}'
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
                _os.replace(tmp_path, CSV_PATH)
                return len(rows_out)
            except PermissionError:
                time.sleep(0.3)
        return 0
    finally:
        if lock_fd is not None:
            try:
                _os.close(lock_fd)
            except Exception:
                pass
            try:
                _os.unlink(lock_path)
            except OSError:
                pass


def main():
    log('[init] starting FULL TrafficVision.Live ingestion v3 (forever)')
    if not os.path.exists(CATALOG_PATH):
        log(f'ERROR: {CATALOG_PATH} not found.')
        sys.exit(1)
    with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
        catalog = json.load(f)
    cams = catalog.get('cameras', [])
    log(f'[init] loaded {len(cams)} cams')

    header = get_header()
    log(f'[init] header: {len(header)} cols')

    cycle_count = 0
    while True:
        cycle_count += 1
        seen_urls, seen_ids, seen_live = load_existing()
        log(f'[cycle {cycle_count}] {len(seen_urls)} URLs, {len(seen_ids)} TV IDs in CSV')

        progress = {'next_idx': 0, 'total_added': 0, 'total_processed': 0}
        if os.path.exists(PROGRESS_PATH):
            try:
                with open(PROGRESS_PATH) as f:
                    progress = json.load(f)
            except Exception:
                pass

        start_idx = progress.get('next_idx', 0)
        total_added_ref = [0]
        total_processed_ref = [0]
        log(f'[cycle {cycle_count}] starting from idx {start_idx}')

        batch = []
        t0 = time.time()
        last_save = t0
        skipped_dup = 0
        skipped_invalid = 0

        for i in range(start_idx, len(cams)):
            rec = cams[i]
            source_meta = rec.get('source', '') or 'tv'
            try:
                result = build_row(rec, source_meta, header)
            except Exception as e:
                log(f'  build_row err at {i}: {e}')
                continue
            if result is None:
                skipped_invalid += 1
                continue
            row_dict, full_id, lower_url = result
            if lower_url in seen_urls or full_id in seen_ids:
                skipped_dup += 1
                continue
            seen_urls.add(lower_url)
            seen_ids.add(full_id)
            batch.append(row_dict)
            total_processed_ref[0] += 1
            if len(batch) >= BATCH_SIZE:
                added = append_batch(batch, header)
                total_added_ref[0] += added
                batch = []
                now = time.time()
                elapsed = now - t0
                rate = total_added_ref[0] / max(elapsed, 1)
                log(f'  progress idx={i+1}/{len(cams)}, added={total_added_ref[0]}, skipped_dup={skipped_dup}, rate={rate:.0f}/s')
                progress['next_idx'] = i + 1
                progress['total_added'] = total_added_ref[0]
                progress['total_processed'] = total_processed_ref[0]
                if now - last_save > 30:
                    with open(PROGRESS_PATH, 'w') as f:
                        json.dump(progress, f)
                    last_save = now
        # Flush remaining
        if batch:
            added = append_batch(batch, header)
            total_added_ref[0] += added
        elapsed = time.time() - t0
        rate = total_added_ref[0] / max(elapsed, 1)
        log(f'[cycle {cycle_count} done] added {total_added_ref[0]} cams, skipped {skipped_dup} dups + {skipped_invalid} invalid, in {elapsed:.1f}s ({rate:.0f}/s)')
        # Reset progress to start from beginning
        with open(PROGRESS_PATH, 'w') as f:
            json.dump({'next_idx': 0, 'total_added': 0, 'total_processed': 0}, f)
        log('[cycle] sleeping 30 min before next cycle...')
        time.sleep(1800)


if __name__ == '__main__':
    main()
