"""Wave-3 super pivot: scrape public cam index sites directly.

Targets:
- AlertCalifornia wildfire cams (UC San Diego ALERT network)
- US National Park Service cams
- US Forest Service cams
- Surf cams (surfline.com, magicseaweed.com, swellinfo.com)
- Traffic cams (511.org sites, Caltrans, etc.)
- Ski cams (ski resort sites)
- Webcam.travel, webcams.travel aggregators
- Earthcam public network

Each source has a known URL or sitemap; we extract cam images + meta.
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
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\wave3_log.txt'


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
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=50, pool_maxsize=200))
    s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=50, pool_maxsize=200))
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


def head_ok(s, url):
    try:
        r = s.head(url, timeout=4, allow_redirects=True, verify=False)
        return 200 <= r.status_code < 400
    except Exception:
        return False


# ---------- alertcalifornia wildfire cams (UCSD ALERT network) ----------
def harvest_alertcalifornia(s, seen, max_pages=80):
    """UCSD ALERTCalifornia wildfire cams — public dataset of ~1000+ cams in CA"""
    # The dataset uses Pinpoint Cameras API
    base = 'https://cameras.alertcalifornia.org/api/public-cameras'
    # Try the actual API; we know the URL pattern from earlier: /public-camera-data/Axis-...
    # It's known to host ~1000 streams, plus we can use the page-level listing
    # Best path: parse the public index of cameras
    pages = [
        'https://cameras.alertcalifornia.org/',
        'https://cameras.alertcalifornia.org/public-camera-data',
        'https://cameras.alertcalifornia.org/data',
    ]
    added = 0
    for page in pages:
        try:
            r = s.get(page, timeout=10, allow_redirects=True, verify=False)
        except Exception:
            continue
        if r.status_code != 200:
            continue
        html = r.text
        # Look for Axis- prefix URLs
        for m in re.finditer(r'(?:src|href|content)="([^"]*Axis-[^"]+\.(?:mp4|mjpg|jpe?g))', html, re.I):
            url = m.group(1)
            if url.startswith('//'):
                url = 'https:' + url
            if url in seen:
                continue
            if not head_ok(s, url):
                continue
            seen.add(url)
            host = re.match(r'https?://([^/]+)', url).group(1)
            try:
                fake_res = {'url': url, 'family': 'alertcalifornia', 'stream_kind': 'mjpeg-multipart',
                           'content_type': 'image/jpeg', 'content_length': 0, 'weight': 25,
                           'host': host, 'port': 443, 'ssl': True, 'http_status': 200}
                geo = {'country': 'US', 'regionName': 'California', 'city': '', 'lat': '', 'lon': '',
                       'isp': '', 'org': 'ALERT California / UC San Diego', 'as': ''}
                entry = csv_writer.entry_from_probe(fake_res, {'source': 'wave3-alert'}, geo)
                entry['project_name'] = 'AlertCalifornia wildfire cam'
                entry['type'] = 'image'
                entry['live_stream_url'] = url
                entry['notes'] = (entry.get('notes', '') + '; alert_public_dataset').strip('; ')
                idx = csv_writer.append_one(entry)
                added += 1
                if added % 50 == 0:
                    log(f'  alertcalifornia +{added}')
            except Exception:
                pass
        if added >= 300:
            break
    return added


# ---------- Webcam.travel aggregator ----------
def harvest_webcam_travel(s, seen, max_pages=10):
    """webcam.travel is a free aggregator without auth."""
    base = 'https://www.webcam.travel/'
    pages = ['', 'map/', 'europe/', 'america/', 'asia/', 'africa/', 'oceania/', 'antarctica/']
    added = 0
    for p in pages:
        try:
            r = s.get(base + p, timeout=10, allow_redirects=True, verify=False)
        except Exception:
            continue
        if r.status_code != 200:
            continue
        # extract cam IDs from /webcam/<slug>-<id>.html
        for m in re.finditer(r'(https?://[^"\']+?/\d+\.html)', r.text):
            pass  # not direct cam URL, just detail pages
        # extract cam imgUrls: data-srcset, data-src, src on imgs containing /cam/, /webcam/, .jpg?ts
        for m in re.finditer(r'(?:src|data-src|srcset)[=:]["\']?(https?://[^"\']*?/(?:cam|webcam|image|img)[^"\']*?\.(?:jpg|jpeg|mjpg))', r.text, re.I):
            url = m.group(1)
            url = url.split(' ')[0].split(',')[0]
            if url in seen:
                continue
            if not head_ok(s, url):
                continue
            seen.add(url)
            try:
                host = re.match(r'https?://([^/]+)', url).group(1)
                proj = host.split('.')[0] if host.split('.')[0] != 'www' else host.split('.')[1]
                fake_res = {'url': url, 'family': 'webcam-travel', 'stream_kind': 'jpeg-frame',
                           'content_type': 'image/jpeg', 'content_length': 0, 'weight': 6,
                           'host': host, 'port': 443 if url.startswith('https') else 80,
                           'ssl': url.startswith('https'), 'http_status': 200}
                geo = {'country': '', 'regionName': '', 'city': '', 'lat': '', 'lon': '',
                       'isp': '', 'org': 'webcam.travel aggregator', 'as': ''}
                entry = csv_writer.entry_from_probe(fake_res, {'source': 'wave3-webcamtravel'}, geo)
                entry['project_name'] = f'{proj} webcam (webcam.travel)'
                entry['type'] = 'image'
                entry['live_stream_url'] = url
                idx = csv_writer.append_one(entry)
                added += 1
            except Exception:
                pass
    return added


# ---------- Windy.com via external aggregator endpoint ----------
def harvest_windy_more(s, seen, cities_per_pass=20):
    """Windy.com public cams have a JSON-list endpoint that returns up to 25 per nearby query."""
    cities = [
        # Diverse additional urban centers: mid-size cities, secondary touristic
        (51.5074, -0.1278, 'London'),          # UK
        (48.8566, 2.3522, 'Paris'),
        (52.5200, 13.4050, 'Berlin'),
        (41.9028, 12.4964, 'Rome'),
        (40.4168, -3.7038, 'Madrid'),
        (52.3676, 4.9041, 'Amsterdam'),
        (48.2082, 16.3738, 'Vienna'),
        (50.0755, 14.4378, 'Prague'),
        (55.6761, 12.5683, 'Copenhagen'),
        (59.3293, 18.0686, 'Stockholm'),
        (60.1699, 24.9384, 'Helsinki'),
        (-33.8688, 151.2093, 'Sydney'),
        (37.5665, 126.9780, 'Seoul'),
        (35.6762, 139.6503, 'Tokyo'),
        (22.3193, 114.1694, 'Hong Kong'),
        (1.3521, 103.8198, 'Singapore'),
        (13.7563, 100.5018, 'Bangkok'),
        (28.6139, 77.2090, 'Delhi'),
        (-22.9068, -43.1729, 'Rio de Janeiro'),
        (19.4326, -99.1332, 'Mexico City'),
        (45.4642, 9.1900, 'Milan'),
        (43.2965, 5.3698, 'Marseille'),
        (45.0703, 7.6869, 'Turin'),
        (38.1157, 13.3613, 'Palermo'),
        (45.6495, 13.7768, 'Trieste'),
        (47.6062, -122.3321, 'Seattle'),
        (45.5051, -122.6750, 'Portland'),
        (32.7157, -117.1611, 'San Diego'),
        (33.4484, -112.0740, 'Phoenix'),
        (39.7392, -104.9903, 'Denver'),
        (29.9511, -90.0715, 'New Orleans'),
        (25.7617, -80.1918, 'Miami'),
        (42.3601, -71.0589, 'Boston'),
        (39.9526, -75.1652, 'Philadelphia'),
        (32.7765, -79.9311, 'Charleston'),
        (44.9778, -93.2650, 'Minneapolis'),
        (38.6270, -90.1994, 'St Louis'),
        (36.1627, -86.7816, 'Nashville'),
        (47.6062, -122.3321, 'Seattle-2'),
        (43.6532, -79.3832, 'Toronto'),
        (45.5017, -73.5673, 'Montreal'),
        (49.2827, -123.1207, 'Vancouver'),
        (-34.6037, -58.3816, 'Buenos Aires'),
        (-12.0464, -77.0428, 'Lima'),
        (4.7110, -74.0721, 'Bogota'),
        (-33.4489, -70.6693, 'Santiago'),
        (-0.1807, -78.4678, 'Quito'),
        (10.6666, -71.6125, 'Maracaibo'),
        (43.7102, 7.2620, 'Monaco'),
        (64.1466, -21.9426, 'Reykjavik'),
        (45.8150, 15.9819, 'Zagreb'),
        (53.3498, -6.2603, 'Dublin'),
        (-37.8136, 144.9631, 'Melbourne'),
        (-36.8485, 174.7633, 'Auckland'),
        (21.3099, -157.8581, 'Honolulu'),
        (-3.4653, -62.2159, 'Manaus'),
        (-16.6864, -49.2643, 'Goiania'),
        (-8.0476, -34.8770, 'Recife'),
        (-22.9068, -43.1729, 'Rio-2'),
        (-15.7942, -47.8822, 'Brasilia'),
        (6.5244, 3.3792, 'Lagos'),
        (-26.2041, 28.0473, 'Johannesburg'),
        (1.2921, 36.8219, 'Nairobi'),
        (-1.2921, 36.8219, 'Nairobi-2'),
        (30.0444, 31.2357, 'Cairo'),
        (31.2001, 29.9187, 'Alexandria'),
        (34.6937, 135.5023, 'Osaka'),
        (34.3853, 132.4553, 'Hiroshima'),
        (43.0642, 141.3469, 'Sapporo'),
        (26.2124, 127.6809, 'Okinawa'),
        (35.0116, 135.7681, 'Kyoto'),
        (37.5665, 126.9780, 'Seoul-2'),
        (22.1987, 113.5439, 'Macau'),
        (39.9042, 116.4074, 'Beijing'),
        (31.2304, 121.4737, 'Shanghai'),
        (30.5728, 104.0668, 'Chengdu'),
        (22.5431, 114.0579, 'Shenzhen'),
        (23.1291, 113.2644, 'Guangzhou'),
        (5.4164, 100.3327, 'Penang'),
        (-6.2088, 106.8456, 'Jakarta'),
        (3.1390, 101.6869, 'KL'),
        (14.5995, 120.9842, 'Manila'),
        (37.4563, 126.7052, 'Incheon'),
        (21.0285, 105.8542, 'Hanoi'),
        (10.8231, 106.6297, 'HCMC'),
        (47.9189, 106.9172, 'Ulaanbaatar'),
        (33.5138, 36.2765, 'Damascus'),
        (33.8938, 35.5018, 'Beirut'),
        (31.7857, 35.2137, 'Jerusalem'),
        (32.0853, 34.7818, 'Tel Aviv'),
        (30.0444, 31.2357, 'Cairo-2'),
        (26.2285, 50.5860, 'Bahrain'),
        (25.2048, 55.2708, 'Dubai'),
        (24.4539, 54.3773, 'Abu Dhabi'),
        (21.4858, 39.1925, 'Jeddah'),
        (24.7136, 46.6753, 'Riyadh'),
        (41.0082, 28.9784, 'Istanbul'),
        (38.4192, 27.1287, 'Izmir'),
    ]
    added = 0
    for lat, lon, name in cities:
        try:
            r = s.get('https://node.windy.com/webcams/v2.0/list',
                     params={'nearby': f'{lat},{lon}', 'radius': 800, 'limit': 30},
                     timeout=10)
        except Exception:
            continue
        if r.status_code != 200:
            continue
        try:
            data = r.json()
        except Exception:
            continue
        cams = data.get('cams', [])
        for cam in cams:
            try:
                url = cam.get('images', {}).get('current', '')
                if not url:
                    url = cam.get('image', {}).get('current', '')
                if not url:
                    continue
                if url in seen:
                    continue
                if not head_ok(s, url):
                    continue
                seen.add(url)
                host = re.match(r'https?://([^/]+)', url).group(1)
                proj_name = name + ' (windy)'
                fake_res = {'url': url, 'family': 'windy', 'stream_kind': 'jpeg-frame',
                           'content_type': 'image/jpeg', 'content_length': 0, 'weight': 6,
                           'host': host, 'port': 443 if url.startswith('https') else 80,
                           'ssl': url.startswith('https'), 'http_status': 200}
                loc = cam.get('location', {})
                geo = {'country': loc.get('country', ''), 'regionName': '',
                       'city': loc.get('city', name), 'lat': lat, 'lon': lon,
                       'isp': '', 'org': 'Windy.com public cams', 'as': ''}
                entry = csv_writer.entry_from_probe(fake_res, {'source': 'wave3-windy-round2'}, geo)
                entry['project_name'] = proj_name
                entry['type'] = 'image'
                entry['live_stream_url'] = url
                idx = csv_writer.append_one(entry)
                added += 1
                if added % 50 == 0:
                    log(f'  windy-r2 +{added}')
            except Exception:
                pass
        time.sleep(0.05)
    return added


def main():
    log('[init] starting Wave-3 super pivot')
    s = session()
    seen = existing_live_urls()
    log(f'[init] {len(seen)} existing live URLs')

    log('[pass-1] alertcalifornia')
    a = harvest_alertcalifornia(s, seen)
    log(f'[alertcalifornia] +{a}')

    log('[pass-2] webcam.travel')
    a = harvest_webcam_travel(s, seen)
    log(f'[webcamtravel] +{a}')

    log('[pass-3] windy-r2')
    a = harvest_windy_more(s, seen, cities_per_pass=20)
    log(f'[windy-r2] +{a}')

    log('[done] Wave-3 complete')


if __name__ == '__main__':
    main()
