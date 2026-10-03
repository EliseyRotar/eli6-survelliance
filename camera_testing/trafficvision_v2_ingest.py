"""Ingest the 235 new TV cams into CSV."""
import csv
import json
import os
import re
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)

CSV_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')
NEW_PATH = Path(r'C:\Users\eli6-admin\AppData\Local\Temp\tv_new_only_v2.json')
LOG_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_live_ingest_log.txt')
BATCH_SIZE = 500

HEADER_37 = [
    'idx', 'project_name', 'url', 'live_stream_url', 'type', 'auth_required',
    'auth_user', 'auth_pass', 'enabled', 'live_status', 'http_status', 'content_type',
    'server_header', 'page_title', 'description', 'category', 'likely_subject',
    'brand', 'model', 'country', 'region', 'city', 'zip', 'address', 'road',
    'location_precision', 'lat', 'lon', 'geo_source', 'isp', 'org', 'asn',
    'reverse_dns', 'host', 'confidence', 'notes', 'csv_id',
]


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def get_live_url(rec):
    video_url = rec.get('videoUrl', '') or ''
    image_url = rec.get('imageUrl', '') or ''
    player_url = rec.get('playerUrl', '') or ''
    youtube_id = rec.get('youtubeVideoId', '') or ''
    ipcam_alias = rec.get('ipcamliveAlias', '') or ''
    source_url = rec.get('sourceUrl', '') or ''
    go2rtc = rec.get('go2rtcWsUrl', '') or ''
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
    if not image_url and angles:
        for ang in angles:
            if isinstance(ang, dict) and ang.get('imageUrl'):
                image_url = ang['imageUrl']
                break
    if player_url:
        return player_url
    elif video_url and ('m3u8' in video_url.lower() or 'mp4' in video_url.lower()):
        return video_url
    elif youtube_id:
        return f'https://www.youtube.com/watch?v={youtube_id}'
    elif ipcam_alias:
        return f'https://ipcamlive.com/{ipcam_alias}'
    elif video_url:
        return video_url
    elif image_url:
        return image_url
    elif go2rtc:
        return go2rtc
    elif source_url:
        return source_url
    return ''


def build_row(rec, idx):
    cam_id = rec.get('id', '') or ''
    if not cam_id:
        return None
    source = rec.get('source', '') or 'tv'
    full_id = f'{source}:{cam_id}'

    live_url = get_live_url(rec)
    if not live_url:
        return None

    m = re.match(r'(?:https?|rtsp|rtmp|wss?)://([^/:?#]+)', live_url)
    host = m.group(1) if m else ''
    if host.startswith('www.'):
        host = host[4:]

    location = rec.get('location', '')
    city = rec.get('city', '')
    state = rec.get('state', '')
    roadway = rec.get('roadway', '')
    direction = rec.get('direction', '')
    description = rec.get('description', '')
    make = rec.get('make', '')
    model = rec.get('model', '')
    county = rec.get('county', '')
    postcode = rec.get('postcode', '')
    road = rec.get('road', '')
    display_name = rec.get('display_name', '')
    feed_type = rec.get('feedType', '')

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
    name = name.replace('\u2013', '-').replace('\u2014', '-')[:100]

    lu = live_url.lower()
    if 'm3u8' in lu:
        ctype = 'application/vnd.apple.mpegurl'
    elif 'mp4' in lu:
        ctype = 'video/mp4'
    elif 'mjpeg' in lu or 'mjpg' in lu:
        ctype = 'multipart/x-mixed-replace'
    else:
        ctype = 'image/jpeg'

    lat = str(rec.get('lat', '') or '')
    lon = str(rec.get('lng', '') or '')
    country = rec.get('country', '')
    region = rec.get('state', '') or rec.get('region', '')
    if isinstance(region, dict):
        region = ''
    cat = rec.get('category', '') or (rec.get('categories', [''])[0] if rec.get('categories') else '')

    notes_parts = [f'trafficvision_id={full_id}']
    if make: notes_parts.append(f'make={make}')
    if model: notes_parts.append(f'model={model}')
    if county: notes_parts.append(f'county={county}')
    if roadway: notes_parts.append(f'roadway={roadway}')
    if direction: notes_parts.append(f'dir={direction}')
    if feed_type: notes_parts.append(f'feedType={feed_type}')
    notes = '; '.join(notes_parts)

    if 'm3u8' in lu or 'mp4' in lu or 'mjpeg' in lu or 'mjpg' in lu or 'ipcamlive' in lu:
        rtype = 'mp4' if '.mp4' in lu else 'hls' if '.m3u8' in lu else 'mjpeg'
    elif 'youtube' in lu or 'youtu.be' in lu:
        rtype = 'youtube'
    else:
        rtype = 'mjpeg' if 'mjpeg' in lu else 'image'

    return {
        'idx': str(idx),
        'project_name': name,
        'url': live_url,
        'live_stream_url': live_url,
        'type': rtype,
        'auth_required': 'False',
        'auth_user': '',
        'auth_pass': '',
        'enabled': 'True',
        'live_status': 'live',
        'http_status': '200',
        'content_type': ctype,
        'server_header': '',
        'page_title': '',
        'description': (description or '')[:200],
        'category': cat or 'public',
        'likely_subject': 'Live public camera' if rtype != 'image' else 'Still image (refreshed)',
        'brand': make or 'TrafficVision',
        'model': model or source,
        'country': country,
        'region': region,
        'city': city,
        'zip': postcode,
        'address': display_name,
        'road': road,
        'location_precision': 'precise' if (lat and lon) else 'host_default',
        'lat': lat,
        'lon': lon,
        'geo_source': 'trafficvision.live',
        'isp': '',
        'org': f'TrafficVision ({source})',
        'asn': '',
        'reverse_dns': '',
        'host': host,
        'confidence': 'high',
        'notes': notes,
        'csv_id': f'tv2_{idx:04d}',
    }


def main():
    log('[init] starting TV v2 ingest')
    log('[init] loading existing CSV for dedup...')
    seen_urls = set()
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            lu = (row.get('live_stream_url', '') or '').lower().strip()
            if lu:
                seen_urls.add(lu)
    log(f'[init] {len(seen_urls):,} existing URLs')

    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        reader = csv.reader(f)
        header = next(reader)
        max_idx = 0
        for r in reader:
            try:
                if r and r[0].isdigit():
                    max_idx = max(max_idx, int(r[0]))
            except Exception:
                pass
    log(f'[init] max idx: {max_idx}')
    next_idx = max_idx + 1

    with open(NEW_PATH, encoding='utf-8') as f:
        cams = json.load(f)
    log(f'[init] loaded {len(cams):,} NEW cams')

    added = 0
    skipped_dup = 0
    batch = []
    t0 = time.time()
    for rec in cams:
        row = build_row(rec, next_idx)
        if not row:
            continue
        live_url = row['live_stream_url']
        if live_url.lower() in seen_urls:
            skipped_dup += 1
            continue
        seen_urls.add(live_url.lower())
        batch.append(row)
        added += 1
        next_idx += 1
        if len(batch) >= BATCH_SIZE:
            with open(CSV_PATH, 'a', encoding='utf-8', newline='') as f:
                w = csv.DictWriter(f, fieldnames=HEADER_37, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
                for r in batch:
                    w.writerow(r)
            batch = []
            log(f'  added {added}, dup {skipped_dup}, {time.time()-t0:.0f}s')
    if batch:
        with open(CSV_PATH, 'a', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=HEADER_37, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
            for r in batch:
                w.writerow(r)
    log(f'\n[done] total {added} added, {skipped_dup} dup')


if __name__ == '__main__':
    main()
