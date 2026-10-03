"""Find new VIDEO cams from sources not yet tried.

Strategy: target known video-friendly IP cam aggregators.
- vlc-wasm hosted streams
- webcamtests
- publiciptv
- ipcamcentral
- digi-host
- webcams.travel  (not yet tried)
- bigbrother.all-in-one  (admin panel cams)
- ispyconnect
- o2dsl (not yet)
- flussbad (no)
- trafficbroadcast
"""
import csv
import os
import time
import json
import re
import urllib.request
import ssl
import random
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

import glob

CSV_PATH = None
for f in glob.glob(r'C:\Users\eli6-admin\Documents\**/controllable_Webcams.csv', recursive=True):
    CSV_PATH = f
    break
if not CSV_PATH:
    print('CSV not found')
    exit(1)
print(f'CSV: {CSV_PATH}')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def fetch(url, timeout=10, binary=False, max_bytes=10*1024*1024):
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            data = r.read(max_bytes)
            ct = r.headers.get('Content-Type', '')
            if not binary:
                try:
                    data = data.decode('utf-8', errors='replace')
                except:
                    pass
            return (r.status, ct, data)
    except urllib.error.HTTPError as e:
        return (e.code, '', b'' if binary else '')
    except Exception as e:
        return (-1, str(e)[:100], b'' if binary else '')


# 1) webcams.travel - well-known cam aggregator with both image and video
def webcams_travel():
    print('\n[1] webcams.travel discovery')
    urls = []
    # /cams/near/<city>
    cities = ['sofia', 'varna', 'burgas', 'ruse', 'plovdiv', 'london', 'paris', 'tokyo', 'berlin', 'rome',
              'amsterdam', 'new-york', 'los-angeles', 'barcelona', 'munich', 'milan', 'vienna', 'prague']
    for city in cities:
        for page in range(1, 6):
            url = f'https://www.webcams.travel/webcam/{city}?p={page}'
            status, ct, html = fetch(url, timeout=10)
            if status == 200 and 'html' in ct:
                # Find cam IDs
                for m in re.finditer(r'webcam/(\d+)', html):
                    cam_id = m.group(1)
                    cam_url = f'https://www.webcams.travel/webcam/{cam_id}'
                    urls.append((cam_url, 'webcams_travel', f'webcams.travel cam {cam_id} ({city})'))
            time.sleep(0.5)
    return urls


# 2) digi-host.de webcam list (DE cams with m3u8)
def digi_host():
    print('\n[2] digi-host.de')
    urls = []
    for cat in ['webcams', 'cams', 'list']:
        for page in range(1, 4):
            url = f'https://www.digi-host.de/{cat}.html?p={page}'
            status, ct, html = fetch(url, timeout=10)
            if status == 200:
                # Find cam URLs
                for m in re.finditer(r'(https?://[^"\s]+\.m3u8)', html, re.I):
                    urls.append((m.group(1), 'digi_host_m3u8', f'digi-host m3u8 from {cat}'))
                for m in re.finditer(r'(https?://[\d\.]+:\d+/(?:axis-cgi|mjpg|cam|video)[^"\s]*)', html, re.I):
                    urls.append((m.group(1), 'digi_host_cam', f'digi-host IP cam from {cat}'))
            time.sleep(0.5)
    return urls


# 3) erlanger webcam list
def erlanger():
    print('\n[3] erlangen webcam list')
    urls = []
    status, ct, html = fetch('https://webcams.ansbach.com/', timeout=10)
    if status == 200:
        for m in re.finditer(r'href="(https?://[^"]+)"', html, re.I):
            u = m.group(1)
            if re.search(r'\.m3u8|\.mp4|mjpg|video|webcam', u, re.I):
                urls.append((u, 'ansbach_cam', f'ansbach webcams.travel-style URL'))
    return urls


# 4) m3u8.tv (free HLS streams)
def m3u8_tv():
    print('\n[4] m3u8.tv')
    urls = []
    # Try common patterns
    for path in ['/channels', '/cams', '/index', '/']:
        url = f'https://m3u8.tv{path}'
        status, ct, html = fetch(url, timeout=8)
        if status == 200:
            for m in re.finditer(r'(https?://[^"\s]+\.m3u8)', html, re.I):
                urls.append((m.group(1), 'm3u8_tv', f'm3u8.tv from {path}'))
    return urls


# 5) city-webcams.eu (German cam aggregator)
def city_webcams_eu():
    print('\n[5] city-webcams.eu')
    urls = []
    for page in range(1, 5):
        url = f'https://www.city-webcams.eu/index.php?id={page}'
        status, ct, html = fetch(url, timeout=10)
        if status == 200:
            for m in re.finditer(r'href="(https?://[^"]+)"', html, re.I):
                u = m.group(1)
                if re.search(r'webcam|cam|mjpg|video|hls|m3u8', u, re.I):
                    urls.append((u, 'city_webcams_eu', f'city-webcams.eu from page {page}'))
    return urls


# 6) OpenTrafficCam (not yet tried - free cam aggregator)
def open_traffic_cam():
    print('\n[6] opencam.org')
    urls = []
    try:
        for page in range(0, 20):
            url = f'https://api.opentrafficcam.org/cams?page={page}'
            status, ct, data = fetch(url, timeout=10)
            if status == 200 and 'json' in ct:
                d = json.loads(data)
                if isinstance(d, list):
                    for cam in d[:50]:
                        if isinstance(cam, dict):
                            u = cam.get('streamUrl') or cam.get('imageUrl') or cam.get('url')
                            if u:
                                urls.append((u, 'open_traffic_cam', f'open-traffic-cam {cam.get("name", "")}'))
                else:
                    cams = d.get('cams') or d.get('cameras') or d.get('results') or []
                    for cam in cams[:50]:
                        if isinstance(cam, dict):
                            u = cam.get('streamUrl') or cam.get('imageUrl') or cam.get('url')
                            if u:
                                urls.append((u, 'open_traffic_cam', f'open-traffic-cam {cam.get("name", "")}'))
    except Exception as e:
        print(f'  err: {e}')
    return urls


# 7) Earthcam free cams
def earthcam():
    print('\n[7] earthcam public')
    urls = []
    for cat in ['cams', 'search', 'popular', 'cities', 'beach', 'ski']:
        url = f'https://www.earthcam.com/{cat}.php'
        status, ct, html = fetch(url, timeout=10)
        if status == 200:
            for m in re.finditer(r'(https?://[^"\s]+\.m3u8)', html, re.I):
                urls.append((m.group(1), 'earthcam_m3u8', f'earthcam m3u8 from {cat}'))
    return urls


def main():
    all_urls = set()

    # Run discoveries in parallel
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {
            ex.submit(webcams_travel): 'webcams.travel',
            ex.submit(digi_host): 'digi-host',
            ex.submit(erlanger): 'erlanger',
            ex.submit(m3u8_tv): 'm3u8.tv',
            ex.submit(city_webcams_eu): 'city-webcams.eu',
            ex.submit(open_traffic_cam): 'opentrafficcam',
            ex.submit(earthcam): 'earthcam',
        }
        for f in as_completed(futs):
            try:
                urls = f.result(timeout=120)
                print(f'  {futs[f]}: {len(urls)} URLs')
                for u, b, n in urls:
                    all_urls.add((u, b, n))
            except Exception as e:
                print(f'  {futs[f]}: ERR {e}')

    print(f'\n[TOTAL] {len(all_urls)} unique URLs discovered')

    # Filter
    seen = set()
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            if row.get('url'):
                seen.add(row['url'])

    # Save to new file for review (don't auto-add)
    out = 'new_video_discovery.csv'
    with open(out, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['url', 'brand', 'notes', 'in_csv'])
        for u, b, n in sorted(all_urls):
            in_csv = 'yes' if u in seen else 'no'
            w.writerow([u, b, n, in_csv])
    print(f'Wrote {out}')

    # Stats
    new = [u for u, _, _ in all_urls if u not in seen]
    print(f'New (not in CSV): {len(new)}')

    if new:
        print(f'\nFirst 30 new URLs:')
        for u in new[:30]:
            print(f'  {u}')


if __name__ == '__main__':
    main()
