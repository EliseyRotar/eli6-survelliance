"""Add Bergamo/Orio al Serio area webcams to CSV.

Sources:
- Windy.com Windy Webcams (cached snapshots) — windsurf cams
- Opencctv.org Bergamo airport cam
- Airport webcams aggregator (Bergamo Orio al Serio Aeroclub)
- A35 BreBeMi highway cams (Autostrade per l'Italia)
"""
import csv
import os
import re
import sys
import time
import urllib.parse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')
import csv_writer

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\orio_log.txt'

# URL list to add (Orio al Serio airport + Bergamo area)
CAM_URLS = [
    # Aeroclub di Bergamo official airport cam
    ('https://www.aeroclub.bg.it/public/webcam/current.jpg', 'Bergamo Airport Aeroclub webcam (45.67, 9.71)'),

    # A4 highway cams near Bergamo (Autostrade per l'Italia)
    ('https://video.autostrade.it/video-frames/dt2/b095c76f-0172-4b08-b60a-b2c83b9d60ae-36-0.jpg', 'A04 km 174.3 Bergamo Ovest'),
    ('https://video.autostrade.it/video-frames/dt2/9136de4a-642b-428f-8aa8-7ce08919f560-16-0.jpg', 'A04 km 178.4 Seriate Est'),
    ('https://video.autostrade.it/video-frames/dt2/323f0c73-1c83-484d-a2c5-6a6750e5db7e-38-0.jpg', 'A04 km 172.6 Bergamo Ovest Milano'),
    ('https://video.autostrade.it/video-frames/dt2/9136de4a-642b-428f-8aa8-7ce08919f560-27-0.jpg', 'A04 km 180.2 Seriate Ovest'),
    ('https://video.autostrade.it/video-frames/dt2/9136de4a-642b-428f-8aa8-7ce08919f560-32-0.jpg', 'A04 km 171.2 Bergamo Est'),
    ('https://video.autostrade.it/video-frames/dt2/9136de4a-642b-428f-8aa8-7ce08919f560-33-0.jpg', 'A04 km 168.8 Dalmine Ovest'),

    # A35 BreBeMi highway cams near Treviglio (south of Orio al Serio)
    ('https://video.autostrade.it/video-frames/dt2/9136de4a-642b-428f-8aa8-7ce08919f560-30-0.jpg', 'A35 BreBeMi Treviglio'),

    # Windy.com cached snapshots for nearby Bergamo cams (imgproxy.windy.com)
    ('https://imgproxy.windy.com/_/preview/plain/current/1793901540/original.jpg?v=2', 'Bergamo Porta Sant Alessandro'),
    ('https://imgproxy.windy.com/_/preview/plain/current/1692802873/original.jpg?v=2', 'Mozzo south-east'),
    ('https://imgproxy.windy.com/_/preview/plain/current/1692802764/original.jpg?v=2', 'Mozzo north-east'),
    ('https://imgproxy.windy.com/_/preview/plain/current/1653930863/original.jpg?v=2', 'Paladina north'),
    ('https://imgproxy.windy.com/_/preview/plain/current/1697547365/original.jpg?v=2', 'Sorisole Monte Canto Alto'),
    ('https://imgproxy.windy.com/_/preview/plain/current/1312185168/original.jpg?v=2', 'Almenno San Salvatore meteo'),
    ('https://imgproxy.windy.com/_/preview/plain/current/1519505807/original.jpg?v=2', 'Albino Fiobbio'),
    ('https://imgproxy.windy.com/_/preview/plain/current/1720361734/original.jpg?v=2', 'Cividate al Piano'),
    ('https://imgproxy.windy.com/_/preview/plain/current/1720351086/original.jpg?v=2', 'Palazzago'),
    ('https://imgproxy.windy.com/_/preview/plain/current/1631856562/original.jpg?v=2', 'Vertova Monte Farno'),
    ('https://imgproxy.windy.com/_/preview/plain/current/1571912829/original.jpg?v=2', 'Treviglio Autostrada A35'),
    ('https://imgproxy.windy.com/_/preview/plain/current/1571912766/original.jpg?v=2', 'Treviglio Prealpi'),
    ('https://imgproxy.windy.com/_/preview/plain/current/1248885715/original.jpg?v=2', 'Iseo Lake Iseo'),
    ('https://imgproxy.windy.com/_/preview/plain/current/1457252653/original.jpg?v=2', 'Sovere Museo Malga Lunga'),
    ('https://imgproxy.windy.com/_/preview/plain/current/1793901698/original.jpg?v=2', 'Crema Castelnuovo'),
    ('https://imgproxy.windy.com/_/preview/plain/current/1512924656/original.jpg?v=2', 'San Giovanni Bianco Chiesa'),
    ('https://imgproxy.windy.com/_/preview/plain/current/1759236976/original.jpg?v=2', 'Clusone'),
    ('https://imgproxy.windy.com/_/preview/plain/current/1291632147/original.jpg?v=2', 'Gandino Rifugio Parafulmine'),
    ('https://imgproxy.windy.com/_/preview/plain/current/1719613363/original.jpg?v=2', 'Seregno west'),
    ('https://imgproxy.windy.com/_/preview/plain/current/1469302221/original.jpg?v=2', 'Bresso Airport'),
]


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
    s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=100))
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=100))
    s.headers.update({'User-Agent': 'Mozilla/5.0'})
    return s


def head_ok(s, url, timeout=8):
    try:
        r = s.head(url, timeout=timeout, allow_redirects=True, verify=False)
        return 200 <= r.status_code < 400
    except Exception:
        return False


def add_to_csv(url, name):
    """Add cam URL to CSV with auto-geo."""
    geo = {'country': '', 'regionName': '', 'city': '', 'lat': '', 'lon': '',
           'isp': '', 'org': 'Bergamo airport area', 'as': '', 'zip': ''}
    # Try to extract location from URL or known mappings
    # All these are in Bergamo province

    # Build host
    parsed = urllib.parse.urlparse(url)
    host_only = parsed.hostname or 'unknown'

    ul = url.lower()
    if '.m3u' in ul:
        kind = 'hls-multipart'
    elif '.mp4' in ul:
        kind = 'hls-mp4'
    elif '.mjpg' in ul or '.mjpeg' in ul:
        kind = 'mjpeg-multipart'
    else:
        kind = 'jpeg-frame'

    ssl = url.startswith('https')
    root = f'{parsed.scheme}://{host_only}'

    fake_res = {
        'url': url, 'family': 'orio-al-serio',
        'stream_kind': kind,
        'content_type': 'image/jpeg', 'content_length': 0,
        'weight': 8,
        'host': host_only, 'port': 443 if ssl else 80,
        'ssl': ssl, 'http_status': 200,
    }
    try:
        entry = csv_writer.entry_from_probe(fake_res, {'source': 'orio-research'}, geo)
        entry['project_name'] = name
        entry['type'] = 'image'
        entry['live_stream_url'] = url
        entry['country'] = 'Italy'
        entry['region'] = 'Lombardy'
        entry['city'] = 'Orio al Serio'
        # Set precise coords from known airport location
        if 'Bergamo Airport' in name or 'Aeroclub' in name:
            entry['lat'] = '45.6700'
            entry['lon'] = '9.7100'
        elif 'A04' in name:
            entry['lat'] = '45.695'
            entry['lon'] = '9.665'
        elif 'A35' in name:
            entry['lat'] = '45.510'
            entry['lon'] = '9.575'
        else:
            entry['lat'] = '45.6700'
            entry['lon'] = '9.7100'
        entry['notes'] = f'orio-research; {name}'
        csv_writer.append_one(entry)
        return True
    except Exception as e:
        log(f'  err adding {url}: {e}')
        return False


def main():
    log('[init] starting Orio al Serio ingest')
    s = session()

    added = 0
    failed = []
    for url, name in CAM_URLS:
        if head_ok(s, url, timeout=8):
            log(f'  OK: {name[:40]:<40} | {url[:60]}')
            if add_to_csv(url, name):
                added += 1
                log(f'    added')
        else:
            log(f'  FAIL: {name[:40]:<40} | {url[:60]}')
            failed.append(url)

    log(f'[done] added {added} of {len(CAM_URLS)} cams')
    if failed:
        log(f'  failed URLs: {failed}')


if __name__ == '__main__':
    main()
