"""Full TrafficVision.Live ingestion — adds all 148,575 cams from the catalog.

Each cam has rich metadata: id, location, roadway, lat/lng, videoUrl, imageUrl,
feedType, description, city, state, county, country, make, model, etc.
"""
import csv
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')
import csv_writer

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\trafficvision_full_log.txt'
PROGRESS_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\trafficvision_full_progress.json'
CATALOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_catalog_full.json'


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


def add_cam(rec, source_default, seen, existing_ids, total_added):
    cam_id = rec.get('id', '')
    if not cam_id:
        return False
    full_id = f'{source_default}:{cam_id}' if source_default else cam_id
    if full_id in existing_ids:
        return False
    # Pick best URL
    video_url = rec.get('videoUrl', '') or ''
    image_url = rec.get('imageUrl', '') or ''
    player_url = rec.get('playerUrl', '') or ''
    youtube_id = rec.get('youtubeVideoId', '') or ''
    ipcam_alias = rec.get('ipcamliveAlias', '') or ''
    source_url = rec.get('sourceUrl', '') or ''
    go2rtc = rec.get('go2rtcWsUrl', '') or ''

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
        return False

    lu = live_url.lower().strip()
    if lu in seen:
        existing_ids.add(full_id)
        return False

    # host
    m = re.match(r'(?:https?|rtsp|rtmp)://([^/:]+)', live_url)
    host = m.group(1) if m else ''
    if host.startswith('www.'):
        host = host[4:]

    # name
    location = rec.get('location', '')
    city = rec.get('city', '')
    state = rec.get('state', '')
    roadway = rec.get('roadway', '')
    direction = rec.get('direction', '')
    description = rec.get('description', '')
    source_meta = rec.get('source', '') or source_default
    name = rec.get('name', '') or location
    if not name:
        name_parts = []
        if roadway:
            name_parts.append(roadway)
        if direction:
            name_parts.append(direction)
        if city:
            name_parts.append(city)
        name = ' - '.join(name_parts) if name_parts else f'{host} cam'
    name = name.replace('\u2013', '-').replace('\u2014', '-')

    # CSV type
    if 'm3u8' in lu:
        kind = 'hls-multipart'
        ctype = 'application/vnd.apple.mpegurl'
    elif 'mp4' in lu:
        kind = 'video-h264-mp4'
        ctype = 'video/mp4'
    elif 'mjpeg' in lu or 'mjpg' in lu:
        kind = 'mjpeg-multipart'
        ctype = 'multipart/x-mixed-replace'
    elif 'image' in rec.get('feedType', '') or 'jpg' in lu or 'jpeg' in lu:
        kind = 'jpeg-frame'
        ctype = 'image/jpeg'
    else:
        kind = 'jpeg-frame'
        ctype = 'image/jpeg'

    lat = rec.get('lat', '')
    lon = rec.get('lng', '')
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

    fake_res = {
        'url': live_url,
        'family': f'trafficvision-{source_meta}',
        'stream_kind': kind,
        'content_type': ctype,
        'content_length': 0,
        'weight': 50 if kind != 'jpeg-frame' else 12,
        'host': host,
        'port': 443 if live_url.startswith('https') else 80,
        'ssl': live_url.startswith('https'),
        'http_status': 200,
    }
    geo = {
        'country': country,
        'regionName': region,
        'city': city,
        'lat': lat,
        'lon': lon,
        'isp': '',
        'org': f'TrafficVision ({source_meta})',
        'as': '',
        '_latlon': (lat, lon),
        'zip': postcode,
        'address': display_name,
        'geo_source': 'trafficvision.live',
    }
    try:
        entry = csv_writer.entry_from_probe(fake_res, {'source': 'trafficvision'}, geo)
        entry['project_name'] = name[:100]
        entry['type'] = 'video' if kind != 'jpeg-frame' else 'image'
        entry['live_stream_url'] = live_url
        existing_notes = entry.get('notes', '')
        notes_extra = f'trafficvision_id={full_id}'
        if make:
            notes_extra += f'; make={make}'
        if model:
            notes_extra += f'; model={model}'
        if county:
            notes_extra += f'; county={county}'
        if roadway:
            notes_extra += f'; roadway={roadway}'
        if direction:
            notes_extra += f'; dir={direction}'
        if feed_type:
            notes_extra += f'; feedType={feed_type}'
        entry['notes'] = (existing_notes + '; ' + notes_extra).strip('; ')
        entry['category'] = cat or 'public'
        idx = csv_writer.append_one(entry)
        if idx:
            seen.add(lu)
            existing_ids.add(full_id)
            total_added[0] += 1
            return True
    except Exception as e:
        log(f'  err cam={cam_id}: {e}')
    return False


def main():
    log('[init] starting FULL TrafficVision.Live ingestion')
    if not os.path.exists(CATALOG_PATH):
        log(f'ERROR: {CATALOG_PATH} not found. Run _tv_capture_full.py first.')
        sys.exit(1)
    with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
        catalog = json.load(f)
    cams = catalog.get('cameras', [])
    log(f'[init] loaded {len(cams)} cams from {CATALOG_PATH}')

    seen = existing_live_urls()
    existing_ids = existing_tv_ids()
    log(f'[init] {len(seen)} existing live URLs, {len(existing_ids)} existing TV IDs')

    progress = load_progress()
    start_idx = progress.get('next_idx', 0)
    total_added_ref = [progress.get('total_added', 0)]
    total_processed_ref = [progress.get('total_processed', 0)]

    log(f'[init] resuming from idx {start_idx}')

    cycle_count = 0
    while start_idx < len(cams):
        cycle_count += 1
        n = 0
        added_cycle = 0
        skipped = 0
        # Pre-filter by source to batch by source
        t0 = time.time()
        for i in range(start_idx, len(cams)):
            rec = cams[i]
            source_meta = rec.get('source', '') or 'tv'
            # Quick skip: if URL already in seen
            video_url = rec.get('videoUrl', '') or ''
            image_url = rec.get('imageUrl', '') or ''
            player_url = rec.get('playerUrl', '') or ''
            youtube_id = rec.get('youtubeVideoId', '') or ''
            ipcam_alias = rec.get('ipcamliveAlias', '') or ''
            go2rtc = rec.get('go2rtcWsUrl', '') or ''
            source_url = rec.get('sourceUrl', '') or ''
            # Build candidate URL quickly
            if player_url:
                cand = player_url.lower().strip()
            elif video_url and ('m3u8' in video_url or 'mp4' in video_url):
                cand = video_url.lower().strip()
            elif youtube_id:
                cand = ('https://www.youtube.com/watch?v=' + youtube_id).lower().strip()
            elif ipcam_alias:
                cand = ('https://ipcamlive.com/' + ipcam_alias).lower().strip()
            elif video_url:
                cand = video_url.lower().strip()
            elif image_url:
                cand = image_url.lower().strip()
            elif go2rtc:
                cand = go2rtc.lower().strip()
            elif source_url:
                cand = source_url.lower().strip()
            else:
                cand = ''
            if not cand:
                skipped += 1
                continue
            if cand in seen:
                existing_ids.add(f'{source_meta}:{rec.get("id", "")}')
                skipped += 1
                continue
            # Add cam
            if add_cam(rec, source_meta, seen, existing_ids, total_added_ref):
                added_cycle += 1
            n += 1
            total_processed_ref[0] += 1
            if n % 500 == 0:
                progress['next_idx'] = i + 1
                progress['total_added'] = total_added_ref[0]
                progress['total_processed'] = total_processed_ref[0]
                save_progress(progress)
                elapsed = time.time() - t0
                rate = n / max(elapsed, 1)
                eta = (len(cams) - i) / max(rate, 1)
                log(f'  progress idx={i+1}/{len(cams)}, added={total_added_ref[0]}, skipped={skipped}, rate={rate:.0f}/s, eta={eta/60:.0f}min')

        # Cycle done
        elapsed = time.time() - t0
        log(f'[cycle {cycle_count} done] {added_cycle} added, {skipped} skipped, total={total_added_ref[0]} in {elapsed:.1f}s')
        existing_ids = existing_tv_ids()
        seen = existing_live_urls()
        total_added_ref[0] = 0
        progress['next_idx'] = start_idx  # don't restart, just keep going
        save_progress(progress)
        log('[cycle] sleeping 30s before continue...')
        time.sleep(30)

    log(f'[done] all cams processed')


if __name__ == '__main__':
    main()
