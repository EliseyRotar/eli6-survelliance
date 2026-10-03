"""Wave-4: surf cam scraper.

Sources:
- surfline.com — has public cams w/ nearcam path
- magicseaweed.com (now MSW) — has cam pages
- swellinfo.com cam pages
- camviews.com public cam directory
- Météo France cam directory (meteofrance.com webcams)

For each, scrape the public HTML, find image/jpg URLs or iframe to cam pages,
then validate and add to CSV.
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
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\wave4_log.txt'


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
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=40, pool_maxsize=200))
    s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=40, pool_maxsize=200))
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    })
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


# ----------- surfline.com -----------
def harvest_surfline(s, seen):
    """surfline.com has public cam pages.
    URL pattern: https://www.surfline.com/surf-cam/...
    Their cam image is at https://cam-...-aws.surfline.com/...
    """
    # Surfline API public cams endpoint
    cams_url = 'https://services.surfline.com/cams-public/v1/cams/region?regionId=all&limit=200'
    added = 0
    try:
        r = s.get(cams_url, timeout=10)
        if r.status_code != 200:
            return 0
        data = r.json()
    except Exception:
        return 0
    cams = data.get('response', {}).get('cams', [])
    if not cams and isinstance(data, list):
        cams = data
    log(f'  surfline returned {len(cams)} cams')
    for cam in cams:
        try:
            cam_id = cam.get('_id', '')
            if not cam_id:
                continue
            # cam image URL — try /image endpoint
            img_urls = []
            for key in ('imageUrl', 'image', 'camImage'):
                if cam.get(key):
                    img_urls.append(cam[key])
            # Surfline serves cam images at /image endpoint
            for variant in ['', '?t=0']:
                for region in ['aws', 'cdn']:
                    u = f'https://cam-{region}.surfline.com/{cam_id}/image{variant}'
                    img_urls.append(u)
            # Also alternate: camimage endpoint
            img_urls.append(f'https://cdn.surfline.com/cams/{cam_id}/image')
            found = False
            for u in img_urls:
                if head_ok(s, u):
                    found = True
                    if u in seen:
                        continue
                    seen.add(u)
                    name = cam.get('name', 'Surfline cam')
                    proj_name = f'{name[:35]} surf-cam (surfline)'
                    host = re.match(r'https?://([^/]+)', u).group(1)
                    fake_res = {'url': u, 'family': 'surfline', 'stream_kind': 'jpeg-frame',
                               'content_type': 'image/jpeg', 'content_length': 0, 'weight': 6,
                               'host': host, 'port': 443, 'ssl': True, 'http_status': 200}
                    geo = {
                        'country': '', 'regionName': '', 'city': name,
                        'lat': cam.get('lat'), 'lon': cam.get('lon'),
                        'isp': '', 'org': 'Surfline', 'as': ''
                    }
                    entry = csv_writer.entry_from_probe(fake_res, {'source': 'wave4-surfline'}, geo)
                    entry['project_name'] = proj_name
                    entry['type'] = 'image'
                    entry['live_stream_url'] = u
                    csv_writer.append_one(entry)
                    added += 1
                    break
        except Exception:
            pass
    return added


# ----------- magicseaweed -----------
def harvest_magicseaweed(s, seen):
    """MSW is dead (redirects to surfline)."""
    return 0


# ----------- webcam.travel (retry, different endpoints) -----------
def harvest_webcam_travel_v2(s, seen):
    """webcam.travel has API-like JSON endpoints."""
    pages = [
        'https://www.webcam.travel/api/webcams?lang=en&limit=200',
        'https://api.webcam.travel/api/webcams?limit=200',
    ]
    added = 0
    for p in pages:
        try:
            r = s.get(p, timeout=10, headers={'Accept': 'application/json'})
        except Exception:
            continue
        if r.status_code != 200:
            continue
        try:
            data = r.json()
        except Exception:
            continue
        cams = data.get('webcams') or data.get('results') or data
        if not isinstance(cams, list):
            continue
        log(f'  webcam.travel returned {len(cams)} cams')
        for cam in cams:
            try:
                if not isinstance(cam, dict):
                    continue
                img_url = (cam.get('image', {}).get('current', {}).get('preview') or
                           cam.get('image', {}).get('current', {}).get('thumbnail') or
                           cam.get('previewUrl') or
                           cam.get('imageUrl'))
                if not img_url:
                    continue
                if img_url in seen:
                    continue
                if not head_ok(s, img_url):
                    continue
                seen.add(img_url)
                host = re.match(r'https?://([^/]+)', img_url).group(1)
                name = cam.get('title') or cam.get('name') or 'webcam.travel cam'
                proj_name = f'{name[:35]} webcam (webcam.travel)'
                loc = cam.get('location', {})
                geo = {
                    'country': loc.get('countryCode') or loc.get('country', ''),
                    'regionName': loc.get('regionName', ''),
                    'city': loc.get('city', ''),
                    'lat': loc.get('latitude'), 'lon': loc.get('longitude'),
                    'isp': '', 'org': 'webcam.travel', 'as': ''
                }
                fake_res = {'url': img_url, 'family': 'webcam-travel', 'stream_kind': 'jpeg-frame',
                           'content_type': 'image/jpeg', 'content_length': 0, 'weight': 6,
                           'host': host, 'port': 443, 'ssl': True, 'http_status': 200}
                entry = csv_writer.entry_from_probe(fake_res, {'source': 'wave4-webcamtravel-v2'}, geo)
                entry['project_name'] = proj_name
                entry['type'] = 'image'
                entry['live_stream_url'] = img_url
                csv_writer.append_one(entry)
                added += 1
            except Exception:
                pass
    return added


# ----------- OpenStreetMap cams (query Overpass API) -----------
def harvest_osm_cams(s, seen):
    """OSM has man_made=surveillance or surveillance:type=cam tags.
    Overpass API can find these."""
    overpass_url = 'https://overpass-api.de/api/interpreter'
    # Query for surveillance cameras worldwide
    query = """
    [out:json][timeout:60];
    (
      node["man_made"="surveillance"]["surveillance:type"="camera"];
      way["man_made"="surveillance"]["surveillance:type"="camera"];
      node["man_made"="surveillance"];
    );
    out center 2000;
    """
    added = 0
    try:
        r = s.post(overpass_url, data={'data': query}, timeout=60)
        if r.status_code != 200:
            return 0
        data = r.json()
    except Exception:
        return 0
    elements = data.get('elements', [])
    log(f'  OSM returned {len(elements)} surveillance cams')
    for el in elements:
        try:
            tags = el.get('tags', {})
            url = tags.get('url') or tags.get('contact:webcam') or tags.get('webcam')
            if not url:
                # try mapillary-style
                continue
            if not url.startswith('http'):
                url = 'http://' + url
            if url in seen:
                continue
            if not head_ok(s, url):
                continue
            seen.add(url)
            host = re.match(r'https?://([^/]+)', url).group(1)
            name = tags.get('name') or tags.get('operator') or 'OSM cam'
            proj_name = f'{name[:35]} cam (OSM)'
            fake_res = {'url': url, 'family': 'osm', 'stream_kind': 'jpeg-frame',
                       'content_type': 'image/jpeg', 'content_length': 0, 'weight': 6,
                       'host': host, 'port': 443 if url.startswith('https') else 80,
                       'ssl': url.startswith('https'), 'http_status': 200}
            loc = el.get('center') or el
            geo = {
                'country': tags.get('addr:country', ''), 'regionName': tags.get('addr:state', ''),
                'city': tags.get('addr:city', ''),
                'lat': loc.get('lat'), 'lon': loc.get('lon'),
                'isp': '', 'org': tags.get('operator', 'OpenStreetMap'), 'as': ''
            }
            entry = csv_writer.entry_from_probe(fake_res, {'source': 'wave4-osm'}, geo)
            entry['project_name'] = proj_name
            entry['type'] = 'image'
            entry['live_stream_url'] = url
            csv_writer.append_one(entry)
            added += 1
        except Exception:
            pass
    return added


# ----------- OpenWeatherMap cams (via their public webcams page) -----------
def harvest_owm(s, seen):
    """openweathermap.org has a list of public weather cams under /cams."""
    pages = ['https://openweathermap.org/cams', 'https://openweathermap.org/api/webcams']
    added = 0
    for p in pages:
        try:
            r = s.get(p, timeout=10)
        except Exception:
            continue
        if r.status_code != 200:
            continue
        for m in re.finditer(r'(?:src|data-src)\s*=\s*["\'](https?://[^"\']*\.(?:jpg|jpeg|png))', r.text, re.I):
            url = m.group(1)
            if url in seen:
                continue
            if not head_ok(s, url):
                continue
            seen.add(url)
            host = re.match(r'https?://([^/]+)', url).group(1)
            proj_name = f'{host[:25]} weather-cam (owm)'
            fake_res = {'url': url, 'family': 'owm', 'stream_kind': 'jpeg-frame',
                       'content_type': 'image/jpeg', 'content_length': 0, 'weight': 6,
                       'host': host, 'port': 443, 'ssl': True, 'http_status': 200}
            geo = {'country': '', 'regionName': '', 'city': '', 'lat': '', 'lon': '',
                   'isp': '', 'org': 'OpenWeatherMap', 'as': ''}
            entry = csv_writer.entry_from_probe(fake_res, {'source': 'wave4-owm'}, geo)
            entry['project_name'] = proj_name
            entry['type'] = 'image'
            entry['live_stream_url'] = url
            csv_writer.append_one(entry)
            added += 1
    return added


def main():
    log('[init] starting Wave-4')
    s = session()
    seen = existing_live_urls()
    log(f'[init] {len(seen)} existing live URLs')

    log('[pass-1] surfline')
    a = harvest_surfline(s, seen)
    log(f'[surfline] +{a}')

    log('[pass-2] webcam.travel v2')
    a = harvest_webcam_travel_v2(s, seen)
    log(f'[webcam.travel-v2] +{a}')

    log('[pass-3] OSM surveillance cams')
    a = harvest_osm_cams(s, seen)
    log(f'[osm] +{a}')

    log('[pass-4] OWM weather cams')
    a = harvest_owm(s, seen)
    log(f'[owm] +{a}')

    log('[done] Wave-4 complete')


if __name__ == '__main__':
    main()
