"""Comprehensive live_env_streams ingestion.

The geojson has 5997 streams with type info:
- url_type: hls | html_page | video_mp4 | m3u8 | skycam | youtube
- source_family: skylinewebcams | opencctv | traffic | ny | youtube | other
- environment: coastal | urban | mountain | traffic | skycam | wildlife | aerial | harbor
- scene_type: beach | city | traffic | ...
- coordinates_quality: exact | city

Build strategy:
- For hls/video URLs: trust directly if HEAD 200
- For html_pages: search the page for embedded <img mjpg/jpg>, <video>, <iframe>, .m3u8
  (skylinewebcams.com cams are direct iframe embeds to media.skylinewebcams.com)
"""
import csv
import json
import os
import re
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')
import csv_writer

from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\live_env2_log.txt'
GEOJSON_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\live_env_streams.geojson'


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
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=80, pool_maxsize=300))
    s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=80, pool_maxsize=300))
    s.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0'})
    return s


def existing_live_urls():
    seen = set()
    if not os.path.exists(CSV_PATH):
        return seen
    with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    for row in rows[1:]:
        u = row[3] if len(row) > 3 else ''
        if u:
            seen.add(u.lower())
    return seen


IMG_URL_RE = re.compile(r'(?:src|href|data-src|data-srcset|srcset)\s*[=:]\s*["\']([^"\']+)', re.I)
JPG_TOKEN_RE = re.compile(r'\.(?:jpe?g|png|mjpg|mp4|m3u8?|ts)(?:\?|$)', re.I)


def extract_image_urls(html, base_url):
    out = []
    try:
        for m in IMG_URL_RE.finditer(html):
            u = m.group(1)
            if u.startswith('data:'):
                continue
            if u.startswith('//'):
                u = 'https:' + u
            if not u.startswith('http'):
                u = urllib.parse.urljoin(base_url, u)
            u = u.split(' ')[0].split(',')[0]
            ul = u.lower()
            if JPG_TOKEN_RE.search(ul):
                out.append(u)
    except Exception:
        pass
    return list(set(out))[:6]


def head_ok(s, url):
    try:
        r = s.head(url, timeout=4, allow_redirects=True, verify=False)
        return 200 <= r.status_code < 400
    except Exception:
        return False


def probe_url(s, url):
    """For an html_page, fetch and find image sub-URL. For media URL, return as-is."""
    try:
        r = s.head(url, timeout=4, allow_redirects=True, verify=False)
    except Exception:
        return None
    if r.status_code >= 400:
        return None
    ct = r.headers.get('Content-Type', '').lower()
    if 'html' in ct or ct.startswith('text/'):
        # fetch full html and search
        try:
            r2 = s.get(url, timeout=10, allow_redirects=True, verify=False)
            if r2.status_code >= 400:
                return None
            html = r2.text[:600_000]
            for u in extract_image_urls(html, url):
                if head_ok(s, u):
                    return u
        except Exception:
            return None
        return None
    if any(t in ct for t in ('image/', 'mpeg', 'octet-stream', 'mp4')):
        return url
    return None


def add_cam(s, seen, proj_name, url, family, stream_kind, ct, country, region, city, lat, lon, org, source_tag):
    if url in seen:
        return False
    seen.add(url)
    try:
        host = re.match(r'(?:https?|rtsp|rtmp)://([^/:]+)', url).group(1)
    except Exception:
        return False
    try:
        fake_res = {'url': url, 'family': family, 'stream_kind': stream_kind,
                   'content_type': ct, 'content_length': 0,
                   'weight': 25 if 'mjpg' in url or 'm3u8' in url or 'mp4' in url else 6,
                   'host': host, 'port': 443 if url.startswith('https') else 80,
                   'ssl': url.startswith('https'), 'http_status': 200}
        geo = {'country': country, 'regionName': region, 'city': city,
               'lat': lat, 'lon': lon, 'isp': '', 'org': org, 'as': ''}
        entry = csv_writer.entry_from_probe(fake_res, {'source': source_tag}, geo)
        entry['project_name'] = proj_name
        entry['type'] = 'image' if stream_kind == 'jpeg-frame' else 'video'
        entry['live_stream_url'] = url
        idx = csv_writer.append_one(entry)
        return True
    except Exception:
        return False


def main():
    log('[init] starting live_env2 ingest')
    s = session()
    seen = existing_live_urls()
    log(f'[init] {len(seen)} existing live URLs')

    with open(GEOJSON_PATH, 'r', encoding='utf-8') as f:
        j = json.load(f)
    features = j.get('features', [])
    log(f'[plan] {len(features)} features')

    added = 0
    # Filter out features whose URL we already have
    pending = []
    for feat in features:
        url = feat['properties'].get('url', '')
        if not url:
            continue
        # Skip empty / placeholder / already-known
        if 'skylinewebcams' in url.lower() and '/webcam/' in url:
            # might be html_page; need to extract inner
            pass
        pending.append(feat)

    log(f'[plan] {len(pending)} features to process')

    # Use ThreadPool for parallel probing
    def process(feat):
        props = feat['properties']
        url = props.get('url', '')
        if not url or url.lower() in seen:
            return False
        url_type = props.get('url_type', '')
        src_family = props.get('source_family', '?')
        coords = feat.get('geometry', {}).get('coordinates', [None, None])
        lon, lat = (coords[0], coords[1]) if len(coords) == 2 else (None, None)
        country = props.get('country_code', '')
        city = props.get('name', '')
        env = props.get('environment', 'urban')
        scene = props.get('scene_type', '')

        # Skip YouTube / non-mjpeg
        if 'youtube.com' in url or 'youtu.be' in url:
            return False
        if url_type in ('youtube', 'other') and 'mjpg' not in url and 'm3u8' not in url and '.mp4' not in url:
            # only treat as live image if extends pattern
            pass

        # Probe for actual stream
        live = probe_url(s, url)
        if not live:
            return False
        if live.lower() in seen:
            return False

        # Determine kind
        ul = live.lower()
        if '.m3u8' in ul or '.m3u' in ul:
            kind = 'hls-multipart'
        elif '.mp4' in ul:
            kind = 'hls-mp4'
        elif '.mjpg' in ul or '/mjpeg' in ul:
            kind = 'mjpeg-multipart'
        else:
            kind = 'jpeg-frame'

        # Build project name
        proj = props.get('display_name', props.get('name', 'live_env cam'))
        proj_full = f'{proj[:30]} (live_env/{src_family}/{env}/{scene})'

        ct = ''
        try:
            r = s.head(live, timeout=4, allow_redirects=True, verify=False)
            ct = r.headers.get('Content-Type', '')
        except Exception:
            pass

        if add_cam(s, seen, proj_full, live, src_family, kind, ct, country, '',
                   city, lat, lon, props.get('source_family', ''), 'live_env2'):
            return True
        return False

    with ThreadPoolExecutor(max_workers=30) as ex:
        futures = [ex.submit(process, f) for f in pending]
        for f in as_completed(futures):
            try:
                if f.result():
                    added += 1
                    if added % 100 == 0:
                        log(f'  +{added}')
            except Exception:
                pass
    log(f'[done] live_env2 +{added}')


if __name__ == '__main__':
    main()
