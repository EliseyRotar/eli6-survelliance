"""TrafficVision.Live bulk ingestor — pulls all 845 source files (155k+ cams).

Each source returns:
- _metadata: source name, website, cameraCount, generated date
- cameras[]: each cam has id, location, roadway, lat, lng, videoUrl, imageUrl,
  feedType, description, city, make, model, country, state, county, postcode, etc.

URL pattern: https://data.trafficvision.live/camera-data/{source_id}-cameras.json
"""
import csv
import json
import os
import re
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')
import csv_writer

from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\trafficvision_log.txt'
PROGRESS_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\trafficvision_progress.json'
SOURCES_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\trafficvision_sources.txt'

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0'


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def session():
    s = requests.Session()
    retries = Retry(total=0)
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=30, pool_maxsize=100))
    s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=30, pool_maxsize=100))
    s.headers.update({'User-Agent': UA, 'Accept': 'application/json'})
    return s


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
    """Track TV cam IDs to avoid re-adding."""
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


def load_sources():
    """Load live sources (pre-filtered by trafficvision_probe.py)."""
    live_path = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\trafficvision_live.txt'
    if not os.path.exists(live_path):
        log(f'ERROR: {live_path} not found. Run trafficvision_probe.py first.')
        sys.exit(1)
    with open(live_path) as f:
        sources = []
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # Format: source_id\tcount
            parts = line.split('\t')
            if parts:
                sources.append(parts[0])
    return sources


def fetch_source(s, source_id):
    """Fetch a single source's camera JSON."""
    url = f'https://data.trafficvision.live/camera-data/{source_id}-cameras.json'
    try:
        r = s.get(url, timeout=20)
        if r.status_code == 404:
            return None, '404'
        if r.status_code == 429:
            return None, '429'
        if r.status_code == 200:
            try:
                return r.json(), 'ok'
            except Exception:
                return None, 'parse_err'
        return None, f'status_{r.status_code}'
    except Exception as e:
        return None, str(e)[:40]


def add_cam(rec, source_id, seen, existing_ids, total_added):
    cam_id = rec.get('id', '')
    if not cam_id:
        return False
    full_id = f'{source_id}:{cam_id}'
    if full_id in existing_ids:
        return False
    video_url = rec.get('videoUrl', '') or ''
    image_url = rec.get('imageUrl', '') or ''
    # Pick best URL (video first, then image)
    if video_url:
        live_url = video_url
        feed_type = 'video'
    elif image_url:
        live_url = image_url
        feed_type = 'image'
    else:
        return False
    if 'playerUrl' in rec and rec.get('playerUrl'):
        live_url = rec['playerUrl']
        feed_type = 'video'
    if 'youtubeVideoId' in rec and rec.get('youtubeVideoId'):
        live_url = f'https://www.youtube.com/watch?v={rec["youtubeVideoId"]}'
        feed_type = 'video'
    if 'go2rtcWsUrl' in rec and rec.get('go2rtcWsUrl'):
        live_url = rec['go2rtcWsUrl']
        feed_type = 'video'
    if 'imageUrlBig' in rec and rec.get('imageUrlBig'):
        live_url = rec['imageUrlBig']
        feed_type = 'image'

    fu = live_url.lower().strip()
    if fu in seen:
        existing_ids.add(full_id)
        return False

    lat = rec.get('lat', '')
    lon = rec.get('lng', '')
    city = rec.get('city', '')
    state = rec.get('state', '')
    country = rec.get('country', '')
    county = rec.get('county', '')
    postcode = rec.get('postcode', '')
    road = rec.get('road', '')
    display_name = rec.get('display_name', '')
    make = rec.get('make', '')
    model = rec.get('model', '')
    location = rec.get('location', '')
    roadway = rec.get('roadway', '')
    direction = rec.get('direction', '')
    description = rec.get('description', '')
    feed_type_meta = rec.get('feedType', '')
    source_meta = rec.get('source', '')

    # host
    m = re.match(r'(?:https?|rtsp|rtmp)://([^/:]+)', live_url)
    host = m.group(1) if m else ''
    if host.startswith('www.'):
        host = host[4:]
    proj_name = f'{name_display(city, state, road, source_id)}'

    # CSV type
    if feed_type == 'video':
        kind = 'video-h264' if 'mp4' in fu or 'hls' in fu or 'm3u8' in fu else 'video'
        if '.m3u8' in fu:
            kind = 'hls-multipart'
        elif '.mp4' in fu:
            kind = 'video-h264-mp4'
    else:
        kind = 'jpeg-frame'

    fake_res = {
        'url': live_url,
        'family': f'trafficvision-{source_id}',
        'stream_kind': kind,
        'content_type': 'application/vnd.apple.mpegurl' if 'm3u8' in fu else 'image/jpeg',
        'content_length': 0,
        'weight': 50 if feed_type == 'video' else 15,
        'host': host,
        'port': 443 if live_url.startswith('https') else 80,
        'ssl': live_url.startswith('https'),
        'http_status': 200,
    }
    geo = {
        'country': country,
        'regionName': state,
        'city': city,
        'lat': lat,
        'lon': lon,
        'isp': '',
        'org': f'TrafficVision ({source_meta or source_id})',
        'as': '',
        '_latlon': (lat, lon),
        'zip': postcode,
        'address': display_name,
        'geo_source': 'trafficvision.live',
    }
    try:
        entry = csv_writer.entry_from_probe(fake_res, {'source': 'trafficvision'}, geo)
        entry['project_name'] = proj_name[:80]
        entry['type'] = 'video' if feed_type == 'video' else 'image'
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
        entry['notes'] = (existing_notes + '; ' + notes_extra).strip('; ')
        entry['category'] = 'public'
        idx = csv_writer.append_one(entry)
        if idx:
            seen.add(fu)
            existing_ids.add(full_id)
            total_added[0] += 1
            return True
    except Exception as e:
        log(f'  err cam={cam_id}: {e}')
    return False


def name_display(city, state, road, source_id):
    parts = []
    if road: parts.append(road)
    if city: parts.append(city)
    if state: parts.append(state)
    if parts:
        return f'{" - ".join(parts)} ({source_id})'
    return f'{source_id} cam'


def main():
    log('[init] starting TrafficVision.Live ingestion')
    s = session()
    seen = existing_live_urls()
    existing_ids = existing_tv_ids()
    log(f'[init] {len(seen)} existing live URLs, {len(existing_ids)} existing TV IDs')

    sources = load_sources()
    log(f'[init] {len(sources)} sources to process')

    progress = load_progress()
    start_idx = progress.get('next_idx', 0)
    total_added_ref = [progress.get('total_added', 0)]
    total_processed_ref = [progress.get('total_processed', 0)]

    cycle_count = 0
    while True:
        cycle_count += 1
        log(f'[cycle {cycle_count}] starting at idx {start_idx}')
        # Use parallel workers (5 concurrent)
        with ThreadPoolExecutor(max_workers=5) as ex:
            futures = {}
            idx = start_idx
            while idx < len(sources) or futures:
                # Submit new sources up to worker limit
                while len(futures) < 5 and idx < len(sources):
                    fut = ex.submit(fetch_source, s, sources[idx])
                    futures[fut] = idx
                    idx += 1
                # Wait for one to complete
                if not futures:
                    break
                done, _ = wait(futures.keys(), timeout=30, return_when=FIRST_COMPLETED)
                for fut in done:
                    si = futures.pop(fut)
                    source_id = sources[si]
                    try:
                        data, status = fut.result()
                    except Exception as e:
                        log(f'  {source_id} err: {e}')
                        data = None
                        status = 'err'
                    if data:
                        cams = data.get('cameras', [])
                        added_this = 0
                        for cam in cams:
                            if add_cam(cam, source_id, seen, existing_ids, total_added_ref):
                                added_this += 1
                        log(f'  [{si}/{len(sources)}] {source_id}: {len(cams)} cams, +{added_this} new (status: {status})')
                        total_processed_ref[0] += len(cams)
                    else:
                        log(f'  [{si}/{len(sources)}] {source_id}: empty/err ({status})')
                    progress['next_idx'] = si + 1
                    progress['total_added'] = total_added_ref[0]
                    progress['total_processed'] = total_processed_ref[0]
                    save_progress(progress)
                time.sleep(0.2)  # small breather to avoid 429s

        # Cycle complete
        log(f'[cycle {cycle_count} done] {total_added_ref[0]} new cams added')
        progress['next_idx'] = 0
        save_progress(progress)
        # Reload existing IDs (other ingestors may have added more)
        existing_ids = existing_tv_ids()
        seen = existing_live_urls()
        total_added_ref[0] = 0
        log('[cycle] sleeping 5 min before next cycle...')
        time.sleep(300)


if __name__ == '__main__':
    main()
