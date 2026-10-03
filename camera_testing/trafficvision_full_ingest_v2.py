"""TV full ingest v2 - batch write for speed."""
import csv
import json
import os
import re
import sys
import time
import io

sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')
import csv_writer

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\trafficvision_full_log.txt'
PROGRESS_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\trafficvision_full_progress.json'
CATALOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_catalog_full.json'

BATCH_SIZE = 500


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def existing_live_urls():
    seen = set()
    if not os.path.exists(CSV_PATH):
        return seen
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        rows = list(csv.reader(f))
    for row in rows[1:]:
        if len(row) > 3 and row[3]:
            seen.add(row[3].lower().strip())
    return seen


def existing_tv_ids():
    ids = set()
    if not os.path.exists(CSV_PATH):
        return ids
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        rows = list(csv.reader(f))
    for row in rows[1:]:
        if len(row) > 33 and row[33]:
            for m in re.finditer(r'trafficvision_id=([^\s;,]+)', row[33]):
                ids.add(m.group(1))
    return ids


def load_progress():
    if os.path.exists(PROGRESS_PATH):
        try:
            with open(PROGRESS_PATH, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {'next_idx': 0, 'total_added': 0, 'total_processed': 0}


def save_progress(p):
    try:
        with open(PROGRESS_PATH, 'w') as f:
            json.dump(p, f)
    except Exception:
        pass


def get_header():
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        return next(csv.reader(f))


def build_row(rec, source_default, header):
    """Build a CSV row from a TV cam record."""
    cam_id = rec.get('id', '')
    if not cam_id:
        return None
    full_id = f'{source_default}:{cam_id}' if source_default else cam_id
    # Pick best URL
    video_url = rec.get('videoUrl', '') or ''
    image_url = rec.get('imageUrl', '') or ''
    player_url = rec.get('playerUrl', '') or ''
    youtube_id = rec.get('youtubeVideoId', '') or ''
    ipcam_alias = rec.get('ipcamliveAlias', '') or ''
    source_url = rec.get('sourceUrl', '') or ''
    go2rtc = rec.get('go2rtcWsUrl', '') or ''
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

    # Build row in column order matching header
    # 0: idx, 1: project_name, 2: url, 3: live_stream_url, 4: type, 5: auth_required,
    # 6: auth_user, 7: auth_pass, 8: enabled, 9: live_status, 10: http_status,
    # 11: content_type, 12: server_header, 13: page_title, 14: description,
    # 15: category, 16: likely_subject, 17: brand, 18: model, 19: country,
    # 20: region, 21: city, 22: zip, 23: address, 24: lat, 25: lon,
    # 26: geo_source, 27: isp, 28: org, 29: asn, 30: reverse_dns, 31: host,
    # 32: confidence, 33: notes, 34: csv_id
    rtype = 'video' if ('m3u8' in lu or 'mp4' in lu or 'mjpeg' in lu or 'mjpg' in lu or 'ipcamlive' in lu or 'youtube' in lu) else 'image'
    if 'youtube' in lu:
        rtype = 'video'

    row = {h: '' for h in header}
    # We'll fill by index instead of name for speed
    row[1] = name[:100]  # project_name
    row[2] = live_url  # url (root)
    row[3] = live_url  # live_stream_url
    row[4] = rtype
    row[5] = 'False'  # auth_required
    row[6] = ''
    row[7] = ''
    row[8] = 'True'
    row[9] = 'live'
    row[10] = '200'
    row[11] = ctype
    row[14] = description[:200]
    row[15] = cat or 'public'
    row[16] = 'Live public camera'
    row[17] = make
    row[18] = model
    row[19] = country
    row[20] = region
    row[21] = city
    row[22] = postcode
    row[23] = display_name
    row[24] = lat
    row[25] = lon
    row[26] = 'trafficvision.live'
    row[27] = ''
    row[28] = f'TrafficVision ({source_meta})'
    row[29] = ''
    row[30] = ''
    row[31] = host
    row[32] = 'high'
    row[33] = notes
    row[34] = ''
    return row, full_id, live_url.lower()


def append_batch(rows, header):
    """Append a batch of rows to CSV atomically."""
    if not rows:
        return 0
    lock_path = CSV_PATH + '.lock'
    lock_fd = None
    import os as _os
    for attempt in range(60):
        try:
            lock_fd = _os.open(lock_path, _os.O_CREAT | _os.O_EXCL | _os.O_RDWR)
            break
        except FileExistsError:
            time.sleep(0.05 + 0.02 * (attempt % 10))
        except Exception:
            time.sleep(0.05)
    if lock_fd is None:
        return 0
    try:
        # Read existing
        with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
            existing = list(csv.reader(f))
        # Find next idx
        max_idx = 0
        for r in existing[1:]:
            try:
                max_idx = max(max_idx, int(r[0]))
            except Exception:
                pass
        next_idx = max_idx + 1
        # Append rows
        for r in rows:
            r[0] = str(next_idx)
            r[34] = f'tv_{next_idx:04d}'
            next_idx += 1
        # Convert dict rows to list rows in header order
        out_rows = []
        for r_dict in rows:
            out_rows.append([str(r_dict.get(h, '')).replace('\r', ' ').replace('\n', ' ') for h in header])
        # Write to temp
        tmp_path = CSV_PATH + '.tmp'
        with open(tmp_path, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
            for r in existing:
                w.writerow(r)
            for r in out_rows:
                w.writerow(r)
        for _ in range(10):
            try:
                _os.replace(tmp_path, CSV_PATH)
                break
            except PermissionError:
                time.sleep(0.2)
        return len(out_rows)
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
    log('[init] starting FULL TrafficVision.Live ingestion v2')
    if not os.path.exists(CATALOG_PATH):
        log(f'ERROR: {CATALOG_PATH} not found.')
        sys.exit(1)
    with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
        catalog = json.load(f)
    cams = catalog.get('cameras', [])
    log(f'[init] loaded {len(cams)} cams')

    header = get_header()
    seen = existing_live_urls()
    existing_ids = existing_tv_ids()
    log(f'[init] {len(seen)} existing live URLs, {len(existing_ids)} existing TV IDs')

    progress = load_progress()
    start_idx = progress.get('next_idx', 0)
    total_added_ref = [progress.get('total_added', 0)]
    total_processed_ref = [progress.get('total_processed', 0)]

    log(f'[init] resuming from idx {start_idx}')

    batch = []
    t0 = time.time()
    while start_idx < len(cams):
        for i in range(start_idx, len(cams)):
            rec = cams[i]
            source_meta = rec.get('source', '') or 'tv'
            result = build_row(rec, source_meta, header)
            if result is None:
                continue
            row_dict, full_id, lower_url = result
            if lower_url in seen:
                existing_ids.add(full_id)
                continue
            seen.add(lower_url)
            existing_ids.add(full_id)
            batch.append(row_dict)
            if len(batch) >= BATCH_SIZE:
                added = append_batch(batch, header)
                total_added_ref[0] += added
                start_idx = i + 1
                progress['next_idx'] = start_idx
                progress['total_added'] = total_added_ref[0]
                save_progress(progress)
                elapsed = time.time() - t0
                rate = total_added_ref[0] / max(elapsed, 1)
                log(f'  progress idx={start_idx}/{len(cams)}, added={total_added_ref[0]}, rate={rate:.0f}/s')
                batch = []
                break  # restart outer loop to save progress
        else:
            # Loop completed
            if batch:
                added = append_batch(batch, header)
                total_added_ref[0] += added
            elapsed = time.time() - t0
            rate = total_added_ref[0] / max(elapsed, 1)
            log(f'[done] all processed: {total_added_ref[0]} cams added in {elapsed:.1f}s ({rate:.0f}/s)')
            break

    log('[exit]')


if __name__ == '__main__':
    main()
