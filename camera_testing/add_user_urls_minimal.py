"""add_user_urls_minimal.py — Add the URLs that work, plus sub-streams found.

Simplified: skip brute-force, just add URLs directly with geo + sub-streams that worked.
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
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\ingest_user_log.txt'

# These URLs are confirmed working from the v3 log
USER_URLS_WORKING = [
    'http://67.166.43.228:50000/img/video.mjpeg',
    'http://190.15.193.92:8085/img/video.mjpeg',
    'http://192.183.2.223:8081/',
    'http://210.62.196.80:8081/',
    'http://38.147.226.28:8081/',
    'http://73.170.30.215:8888/',
    'http://73.170.30.215:8081/',
    'http://201.188.88.64:8080/',
    'http://86.143.65.63:8080/',
    'http://217.211.95.232:8081/',
    'http://187.110.127.220:8888/',
    'http://24.78.151.146/',
    'http://172.101.22.35:8888/',
    'http://192.143.94.237:8081/',
    'http://209.71.59.178:8081/',
    'http://67.161.150.146:8081/',
    'http://162.229.14.147:8081/',
    'http://109.206.96.98:8080/',
    'http://109.206.96.230:8080/',
    'http://109.206.96.96:8080/',
    'http://109.206.96.127:8080/',
    'http://109.206.96.247:8080/',
    'http://93.255.29.119:8080/',
    'http://109.233.220.234:8080/',
]

# Sub-streams that were confirmed working
SUB_STREAMS = [
    'http://93.255.29.119:8080/cam_1.mjpg',
    'http://93.255.29.119:8080/cam_3.mjpg',
    'http://109.206.96.247:8080/cam_1.mjpg',
    'http://109.206.96.247:8080/cam_3.mjpg',
    'http://109.206.96.127:8080/cam_1.mjpg',
    'http://109.206.96.127:8080/cam_2.mjpg',
    'http://109.206.96.127:8080/cam_3.mjpg',
    'http://109.206.96.230:8080/cam_1.mjpg',
    'http://109.206.96.230:8080/cam_2.mjpg',
    'http://109.206.96.230:8080/cam_3.mjpg',
    'http://109.206.96.96:8080/cam_1.mjpg',
    'http://109.206.96.96:8080/cam_2.mjpg',
    'http://109.206.96.96:8080/cam_3.mjpg',
]

# Multi-cam hosts with /img/ paths (Beograd, MBC Bamberg pattern)
IMG_SUBS = [
    ('109.206.96.98', 8080),
    ('109.206.96.230', 8080),
    ('109.206.96.96', 8080),
    ('109.206.96.127', 8080),
    ('109.206.96.247', 8080),
    ('93.255.29.119', 8080),
]
# Common /img/ paths for WebcamXP / Webcam-server
IMG_PATHS = [
    '/img/video.mjpeg',
    '/img/snapshot.jpg',
    '/img/snapshot.cgi?0',
    '/img/snapshot.cgi?1',
    '/img/snapshot.cgi?2',
    '/img/snapshot.cgi?3',
    '/img/main.cgi?next_file=main.htm',
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


def head_video(s, url, timeout=3):
    try:
        r = s.head(url, timeout=timeout, allow_redirects=True, verify=False)
        if r.status_code >= 400:
            return False
        ct = r.headers.get('Content-Type', '').lower()
        if any(t in ct for t in ('image/', 'multipart/', 'video/')):
            return True
        if 'text/plain' in ct or 'octet-stream' in ct:
            try:
                cl = int(r.headers.get('Content-Length', 0) or 0)
                if cl > 1000:
                    return True
            except Exception:
                pass
        return False
    except Exception:
        return False


def add_to_csv(url, source='user-provided', extra_notes=''):
    parsed = urllib.parse.urlparse(url)
    host_only = parsed.hostname
    port = parsed.port or 80
    geo = {'country': '', 'regionName': '', 'city': '', 'lat': '', 'lon': '',
           'isp': '', 'org': 'User-provided URL', 'as': '', 'zip': ''}
    try:
        r = requests.get(f'http://ip-api.com/json/{host_only}?fields=status,country,regionName,city,zip,lat,lon,isp,org,as',
                         timeout=6)
        if r.status_code == 200:
            data = r.json()
            if data.get('status') == 'success':
                geo['country'] = data.get('country', '')
                geo['regionName'] = data.get('regionName', '')
                geo['city'] = data.get('city', '')
                geo['lat'] = str(data.get('lat', ''))
                geo['lon'] = str(data.get('lon', ''))
                geo['isp'] = data.get('isp', '')
                geo['org'] = data.get('org', 'User-provided URL')
                geo['as'] = data.get('as', '')
                geo['zip'] = str(data.get('zip', ''))
    except Exception:
        pass

    ul = url.lower()
    if '.m3u' in ul:
        kind = 'hls-multipart'
    elif '.mp4' in ul:
        kind = 'hls-mp4'
    elif '.mjpg' in ul or '.mjpeg' in ul:
        kind = 'mjpeg-multipart'
    elif 'axis-cgi/media' in ul or 'axis-media' in ul:
        kind = 'h264-matroska'
    else:
        kind = 'jpeg-frame'

    ssl = url.startswith('https')
    fake_res = {
        'url': url, 'family': 'user-provided',
        'stream_kind': kind,
        'content_type': 'image/jpeg', 'content_length': 0,
        'weight': 25 if 'mjpg' in ul or 'm3u' in ul else 6,
        'host': host_only, 'port': port, 'ssl': ssl, 'http_status': 200,
    }
    try:
        entry = csv_writer.entry_from_probe(fake_res, {'source': source}, geo)
        entry['project_name'] = f'User cam at {host_only}'
        entry['type'] = 'image' if kind == 'jpeg-frame' else 'video'
        entry['live_stream_url'] = url
        if extra_notes:
            entry['notes'] = (entry.get('notes', '') + '; ' + extra_notes)[:500]
        csv_writer.append_one(entry)
        return True
    except Exception as e:
        log(f'  err adding {url}: {e}')
        return False


def main():
    log('[init] adding user URLs (minimal)')
    s = session()

    # Phase 1: Add working user URLs
    added = 0
    log(f'[phase 1] adding {len(USER_URLS_WORKING)} user URLs')
    for url in USER_URLS_WORKING:
        if add_to_csv(url, 'user-provided', 'user-provided'):
            added += 1
            log(f'  added: {url}')

    # Phase 2: Add confirmed sub-streams
    log(f'[phase 2] adding {len(SUB_STREAMS)} confirmed sub-streams')
    for url in SUB_STREAMS:
        if add_to_csv(url, 'user-substream', 'user-substream'):
            added += 1
            log(f'  added sub: {url}')

    # Phase 3: Probe /img/ paths on multi-cam hosts (with short timeout)
    log(f'[phase 3] probing /img/ paths on {len(IMG_SUBS)} multi-cam hosts')
    for host, port in IMG_SUBS:
        for pat in IMG_PATHS:
            url = f'http://{host}:{port}{pat}'
            if head_video(s, url, timeout=2):
                if add_to_csv(url, 'user-substream', 'user-substream'):
                    added += 1
                    log(f'  added img: {url}')

    log(f'[done] added {added} new cams from user URLs')


if __name__ == '__main__':
    main()
