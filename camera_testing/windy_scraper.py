"""Windy.com Webcams API scraper.

Uses node.windy.com/webcams/v2.0/list (anonymous-accessible) to harvest
public webcams across the world. With lat/lon "nearby" parameter we
can scan a grid of urban centers and pull ~25 cams per request.

Without an API key we only get the JPG snapshot URL, not the HLS stream,
but it's still useful for monitoring (poll the JPG, append to CSV).
With X-WINDY-API-KEY env we get stream=url for direct m3u8 playback.

The yields without auth: ~5-50 cams per call, ~25 cams per call average.
Output: ./camera_testing/windy_cams.csv + append LIVE rows to our controllable_Webcams.csv.
"""
import csv
import json
import os
import random
import re
import sys
import time
import urllib.parse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\windy_log.txt'

sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')
import csv_writer
import probe_lib

# 80+ major cities across all continents. Each is a "nearby" probe center.
CITY_CENTERS = [
    # North America
    (40.7128, -74.0060),   # NYC
    (34.0522, -118.2437),  # LA
    (41.8781, -87.6298),   # Chicago
    (37.7749, -122.4194),  # SF
    (43.6532, -79.3832),   # Toronto
    (45.5017, -73.5673),   # Montreal
    (19.4326, -99.1332),   # Mexico City
    (45.4215, -75.6972),   # Ottawa
    (37.0902, -95.7129),   # Center USA
    (32.7767, -96.7970),   # Dallas
    (47.6062, -122.3321),  # Seattle
    (39.7392, -104.9903),  # Denver
    (29.7604, -95.3698),   # Houston
    (33.4484, -112.0740),  # Phoenix
    (36.1627, -86.7816),   # Nashville
    (38.9072, -77.0369),   # Washington DC
    (42.3601, -71.0589),   # Boston
    (35.2271, -80.8431),   # Charlotte
    (25.7617, -80.1918),   # Miami
    # Europe
    (51.5074, -0.1278),    # London
    (48.8566, 2.3522),     # Paris
    (52.5200, 13.4050),    # Berlin
    (41.9028, 12.4964),    # Rome
    (40.4168, -3.7038),    # Madrid
    (52.3676, 4.9041),     # Amsterdam
    (50.8503, 4.3517),     # Brussels
    (48.2082, 16.3738),    # Vienna
    (50.0755, 14.4378),    # Prague
    (59.3293, 18.0686),    # Stockholm
    (55.6761, 12.5683),    # Copenhagen
    (60.1699, 24.9384),    # Helsinki
    (53.3498, -6.2603),    # Dublin
    (38.7223, -9.1393),    # Lisbon
    (59.9139, 10.7522),    # Oslo
    (47.3769, 8.5417),     # Zurich
    (46.9480, 7.4474),     # Bern
    (49.4530, 11.0769),    # Nuremberg
    (50.1109, 8.6821),     # Frankfurt
    (53.5511, 9.9937),     # Hamburg
    (51.3397, 12.3731),    # Leipzig
    (48.7758, 9.1829),     # Stuttgart
    (52.3759, 9.7320),     # Hannover
    (54.3233, 10.1398),    # Kiel
    (53.6300, 11.4010),    # Schwerin
    (52.0907, 11.0238),    # Magdeburg
    (50.9290, 11.5859),    # Erfurt
    (51.4812, 11.0039),    # Halle
    (45.4642, 9.1900),     # Milan
    (43.7228, 10.4017),    # Pisa
    (40.8518, 14.2681),    # Naples
    (45.4064, 12.3669),    # Venice
    (44.4949, 11.3426),    # Bologna
    (50.0755, 14.4378),    # Prague
    (45.8150, 15.9819),    # Zagreb
    (47.4979, 19.0402),    # Budapest
    (44.4268, 26.1025),    # Bucharest
    (42.6977, 23.3219),    # Sofia
    (43.8563, 22.7858),    # Sofia City
    (41.9981, 21.4254),    # Skopje
    # Asia
    (35.6762, 139.6503),   # Tokyo
    (37.5665, 126.9780),   # Seoul
    (39.9042, 116.4074),   # Beijing
    (31.2304, 121.4737),   # Shanghai
    (22.3193, 114.1694),   # Hong Kong
    (25.0330, 121.5654),   # Taipei
    (13.7563, 100.5018),   # Bangkok
    (1.3521, 103.8198),    # Singapore
    (14.5995, 120.9842),   # Manila
    (21.0285, 105.8542),   # Hanoi
    (10.8231, 106.6297),   # HCMC
    (3.1390, 101.6869),    # KL
    (-6.2088, 106.8456),   # Jakarta
    (28.6139, 77.2090),    # Delhi
    (19.0760, 72.8777),    # Mumbai
    (12.9716, 77.5946),    # Bangalore
    (13.0827, 80.2707),    # Chennai
    (22.5726, 88.3639),    # Kolkata
    (17.3850, 78.4867),    # Hyderabad
    # Middle East
    (25.2048, 55.2708),    # Dubai
    (24.7136, 46.6753),    # Riyadh
    (31.7683, 35.2137),    # Jerusalem
    (32.0853, 34.7818),    # Tel Aviv
    (41.0082, 28.9784),    # Istanbul
    # Africa
    (-26.2041, 28.0473),   # Johannesburg
    (-33.9249, 18.4241),   # Cape Town
    (-1.2921, 36.8219),    # Nairobi
    (30.0444, 31.2357),    # Cairo
    (6.5244, 3.3792),      # Lagos
    # LATAM
    (-23.5505, -46.6333),  # São Paulo
    (-22.9068, -43.1729),  # Rio
    (4.7110, -74.0721),    # Bogotá
    (-34.6037, -58.3816),   # Buenos Aires
    (-33.4489, -70.6693),   # Santiago
    (-12.0464, -77.0428),  # Lima
    (10.6666, -71.6125),    # Maracaibo
    # Oceania
    (-33.8688, 151.2093),  # Sydney
    (-37.8136, 144.9631),  # Melbourne
    (-36.8485, 174.7633),  # Auckland
    (-33.0572, 115.9420),  # Busselton
    (-41.2865, 174.7762),  # Wellington
    (-43.5321, 172.6378),  # Christchurch
]

API = 'https://node.windy.com/webcams/v2.0/list'


def session():
    s = requests.Session()
    retries = Retry(total=0)
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=30, pool_maxsize=60))
    s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=30, pool_maxsize=60))
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Origin': 'https://www.windy.com',
        'Referer': 'https://www.windy.com/',
    })
    return s


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def existing_hosts():
    seen = set()
    if not os.path.exists(CSV_PATH):
        return seen
    with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    for row in rows[1:]:
        for cell in row:
            if not cell:
                continue
            for m in re.finditer(r'(?:https?|rtsp|rtmp|mms)://([^/]+)', cell):
                seen.add(m.group(1).lower())
    return seen


def fetch_windy_around(s, lat, lon, radius=250):
    """Return list of cams returned by Windy nearby call."""
    try:
        r = s.get(API, params={
            'nearby': f'{lat},{lon}',
            'radius': radius,
            'limit': 25,
            'offset': 0,
            'order': 'popularity',
            'lang': 'en',
            'imageSize': 'preview',
        }, timeout=12)
        if r.status_code != 200:
            return []
        data = r.json()
        return data.get('cams', data.get('webcams', [])) or []
    except Exception:
        return []


def process_cam(cam, s, seen, added_count):
    """Add a single Windy cam to our CSV if not seen."""
    wid = cam.get('id')
    if not wid:
        return False
    title = cam.get('title', '') or ''
    loc = cam.get('location') or {}
    country = loc.get('country', '') or ''
    region = loc.get('region', '') or ''
    city = loc.get('city', '') or ''
    lat = loc.get('lat')
    lon = loc.get('lon')
    imgs = cam.get('images') or {}
    jpg_url = imgs.get('current', '') or imgs.get('preview', '')
    if not jpg_url:
        return False
    # Skip already-seen by cam id (independent URL even if shared host)
    if f'windy:{wid}' in seen:
        return False

    # Verify the JPG URL is alive (HEAD)
    try:
        r = s.head(jpg_url, timeout=4, allow_redirects=True, verify=False)
        if r.status_code >= 400:
            return False
    except Exception:
        return False

    # Add to CSV — type as 'image' since Windy still JPEGs (no HLS key)
    fake_res = {
        'url': jpg_url,
        'family': 'windy-jpeg',
        'stream_kind': 'jpeg-frame',
        'content_type': 'image/jpeg',
        'content_length': 0,
        'weight': 12,
        'host': jpg_url.split('/')[2],
        'port': 443,
        'ssl': True,
        'http_status': 200,
    }
    geo = {
        'country': country,
        'regionName': region,
        'city': city,
        'lat': lat or '',
        'lon': lon or '',
        'isp': '',
        'org': 'Windy.com Webcams',
        'as': '',
    }
    try:
        entry = csv_writer.entry_from_probe(fake_res, {'source': 'windy_com'}, geo)
        idx = csv_writer.append_one(entry)
        seen.add(f'windy:{wid}')
        return True
    except Exception:
        return False


def main():
    s = session()
    seen = existing_hosts()
    log(f'[init] {len(seen)} existing hosts')

    total = 0
    added = 0
    cams = []

    random.shuffle(CITY_CENTERS)  # randomize order each run

    for i, (lat, lon) in enumerate(CITY_CENTERS):
        for radius in [250, 800]:  # near + broad
            log(f'[{i+1}/{len(CITY_CENTERS)}] ({lat},{lon}) r={radius}')
            res = fetch_windy_around(s, lat, lon, radius)
            log(f'  got {len(res)} cams')
            total += len(res)
            cams.extend(res)
            time.sleep(0.2)  # be polite
            if len(cams) >= 200:
                # process batch
                log(f'processing batch of {len(cams)} cams')
                # dedupe by id
                seen_ids = set()
                unique = []
                for c in cams:
                    if c.get('id') not in seen_ids:
                        seen_ids.add(c.get('id'))
                        unique.append(c)
                for cam in unique:
                    if process_cam(cam, s, seen, added):
                        added += 1
                log(f'  added {added} so far')
                cams = []

    # remaining
    if cams:
        log(f'final batch of {len(cams)} cams')
        seen_ids = set()
        unique = []
        for c in cams:
            if c.get('id') not in seen_ids:
                seen_ids.add(c.get('id'))
                unique.append(c)
        for cam in unique:
            if process_cam(cam, s, seen, added):
                added += 1
    log(f'[done] total cams seen={total}, added={added}')


if __name__ == '__main__':
    main()
