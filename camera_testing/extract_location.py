"""Tier 2: HTML scraper for cam landing pages.

For each IP-traced cam, GET the base URL (strip /cam_1.cgi etc.) and parse:
- <title> — extract city/place name
- <meta name="geo.position"> / og:latitude / og:longitude / geo.placename / geo.region
- JSON-LD Place schemas with GeoCoordinates
- Embedded Google Maps / Leaflet / OSM iframes with lat/lon in URL
- HTML comments with lat/lon hints

Output: updates lat/lon/city/region/address in CSV.
"""
import csv
import os
import re
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOG_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\extract_loc_log.txt'


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
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=100, pool_maxsize=200))
    s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=100, pool_maxsize=200))
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    })
    return s


# Patterns to extract location info
RE_GEO_POSITION = re.compile(r'<meta[^>]+name=["\']geo\.position["\'][^>]+content=["\']([^\'"]+)["\']', re.I)
RE_GEO_PLACENAME = re.compile(r'<meta[^>]+name=["\']geo\.placename["\'][^>]+content=["\']([^\'"]+)["\']', re.I)
RE_GEO_REGION = re.compile(r'<meta[^>]+name=["\']geo\.region["\'][^>]+content=["\']([^\'"]+)["\']', re.I)
RE_OG_LAT = re.compile(r'<meta[^>]+property=["\']og:latitude["\'][^>]+content=["\']([^\'"]+)["\']', re.I)
RE_OG_LON = re.compile(r'<meta[^>]+property=["\']og:longitude["\'][^>]+content=["\']([^\'"]+)["\']', re.I)
RE_OG_LOCALE = re.compile(r'<meta[^>]+property=["\']og:locality["\'][^>]+content=["\']([^\'"]+)["\']', re.I)
RE_TITLE = re.compile(r'<title>([^<]+)</title>', re.I)
RE_HTML_COMMENT = re.compile(r'<!--(.*?)-->', re.DOTALL)
RE_LATLON_COMMENT = re.compile(r'lat[^"\']*?([-+]?\d{1,3}\.\d{2,})[^"\']*?lon[^"\']*?([-+]?\d{1,3}\.\d{2,})', re.I)
RE_GMAP_URL = re.compile(r'!3d([-+]?\d+\.\d+)!4d([-+]?\d+\.\d+)', re.I)
RE_GMAP_QUERY = re.compile(r'maps\.google\..*?q=([-+]?\d+\.\d+),([-+]?\d+\.\d+)', re.I)
RE_LEAFLET = re.compile(r'lat[=:]\s*([-+]?\d+\.\d+)[^"]*?lon[=:]\s*([-+]?\d+\.\d+)', re.I)
RE_JSONLD = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.DOTALL | re.I)


def extract_from_html(html):
    """Return dict with lat, lon, city, region, address, raw_tags."""
    result = {'lat': '', 'lon': '', 'city': '', 'region': '', 'address': '', 'raw': []}

    # 1. <meta name="geo.position">lat,lon
    m = RE_GEO_POSITION.search(html)
    if m:
        parts = re.split(r'[;,\s]+', m.group(1).strip())
        if len(parts) >= 2:
            try:
                lat = float(parts[0]); lon = float(parts[1])
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    result['lat'] = str(lat)
                    result['lon'] = str(lon)
                    result['raw'].append('meta:geo.position')
            except ValueError:
                pass

    # 2. og:latitude / og:longitude
    if not result['lat']:
        m1 = RE_OG_LAT.search(html); m2 = RE_OG_LON.search(html)
        if m1 and m2:
            try:
                lat = float(m1.group(1)); lon = float(m2.group(1))
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    result['lat'] = str(lat); result['lon'] = str(lon)
                    result['raw'].append('meta:og:latlon')
            except ValueError:
                pass

    # 3. Google Maps URL with !3d!4d
    if not result['lat']:
        m = RE_GMAP_URL.search(html)
        if m:
            try:
                lat = float(m.group(1)); lon = float(m.group(2))
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    result['lat'] = str(lat); result['lon'] = str(lon)
                    result['raw'].append('gmap:!3d!4d')
            except ValueError:
                pass

    if not result['lat']:
        m = RE_GMAP_QUERY.search(html)
        if m:
            try:
                lat = float(m.group(1)); lon = float(m.group(2))
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    result['lat'] = str(lat); result['lon'] = str(lon)
                    result['raw'].append('gmap:q=')
            except ValueError:
                pass

    # 4. Leaflet inline coords
    if not result['lat']:
        m = RE_LEAFLET.search(html)
        if m:
            try:
                lat = float(m.group(1)); lon = float(m.group(2))
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    result['lat'] = str(lat); result['lon'] = str(lon)
                    result['raw'].append('leaflet:latlon')
            except ValueError:
                pass

    # 5. HTML comments
    if not result['lat']:
        for c in RE_HTML_COMMENT.findall(html):
            m = RE_LATLON_COMMENT.search(c)
            if m:
                try:
                    lat = float(m.group(1)); lon = float(m.group(2))
                    if -90 <= lat <= 90 and -180 <= lon <= 180:
                        result['lat'] = str(lat); result['lon'] = str(lon)
                        result['raw'].append('html-comment')
                        break
                except ValueError:
                    pass

    # 6. JSON-LD Place
    if not result['lat']:
        for jld in RE_JSONLD.findall(html):
            try:
                import json
                data = json.loads(jld)
                # Walk for Place/GeoCoordinates
                if isinstance(data, dict):
                    tp = data.get('@type', '')
                    if 'Place' in (tp if isinstance(tp, list) else [tp]):
                        geo = data.get('geo', {})
                        if isinstance(geo, dict):
                            lat = geo.get('latitude'); lon = geo.get('longitude')
                            if lat and lon:
                                try:
                                    latf = float(lat); lonf = float(lon)
                                    if -90 <= latf <= 90 and -180 <= lonf <= 180:
                                        result['lat'] = str(latf); result['lon'] = str(lonf)
                                        result['raw'].append('jsonld:Place.geo')
                                        if data.get('name'):
                                            result['address'] = data['name']
                                        if data.get('address', {}).get('addressLocality'):
                                            result['city'] = data['address']['addressLocality']
                                        if data.get('address', {}).get('addressRegion'):
                                            result['region'] = data['address']['addressRegion']
                                        if data.get('address', {}).get('streetAddress'):
                                            result['address'] = data['address']['streetAddress']
                                except ValueError:
                                    pass
            except Exception:
                pass

    # 7. Title-based city hint
    m = RE_TITLE.search(html)
    title = m.group(1).strip() if m else ''
    if title and not result['city']:
        # Patterns: "Webcam in <City>", "<City> Webcam", "Cam - <Place> - <Country>"
        t = unescape(title)
        for pat in [
            r'(?:in|at|near|sur)\s+([A-Z][a-zA-Z\-\s\']+?)(?:,|\s*-|\s*$|\s*<)',
            r'^([A-Z][a-zA-Z\-\s\']+?)\s+(?:Webcam|Cam|Web)',
            r'^([A-Z][a-zA-Z\-\s\']+?)\s*[-–]',
        ]:
            mm = re.search(pat, t)
            if mm:
                place = mm.group(1).strip()
                if 2 < len(place) < 60 and not place.lower() in ('cam', 'webcam', 'live', 'livecam'):
                    result['city'] = place
                    result['raw'].append(f'title:{pat[:15]}')
                    break

    # 8. meta geo.placename
    if not result['city']:
        m = RE_GEO_PLACENAME.search(html)
        if m:
            result['city'] = m.group(1).strip()[:80]
            result['raw'].append('meta:geo.placename')

    # 9. meta og:locality
    if not result['city']:
        m = RE_OG_LOCALE.search(html)
        if m:
            result['city'] = m.group(1).strip()[:80]
            result['raw'].append('meta:og:locality')

    # 10. meta geo.region
    if not result['region']:
        m = RE_GEO_REGION.search(html)
        if m:
            result['region'] = m.group(1).strip()[:80]
            result['raw'].append('meta:geo.region')

    return result


def base_url(stream_url):
    """Convert cam stream URL to landing page URL.

    Strips /cam_1.cgi, /video.cgi, /mjpg/video.mjpg, /streaming/channels/101,
    /ISAPI/Streaming/channels/1/picture, /axis-cgi/media.cgi etc.

    Keeps the host root, then we try common landing paths.
    """
    u = stream_url
    parsed = urllib.parse.urlparse(u)
    host = parsed.netloc
    scheme = parsed.scheme
    # Most cam stream paths are subdirectories — try the host root
    candidates = [
        f'{scheme}://{host}/',
        f'{scheme}://{host}/index.html',
        f'{scheme}://{host}/home',
        f'{scheme}://{host}/home.html',
        f'{scheme}://{host}/index.htm',
        f'{scheme}://{host}/cam',
        f'{scheme}://{host}/webcam',
        f'{scheme}://{host}/live',
    ]
    return candidates


def fetch_url(s, url, timeout=4):
    try:
        r = s.get(url, timeout=timeout, allow_redirects=True, verify=False, stream=False)
        if r.status_code >= 400:
            return None
        ct = r.headers.get('Content-Type', '').lower()
        if 'html' in ct or 'xml' in ct or 'text/' in ct or 'json' in ct:
            return r.text[:400_000]
    except Exception:
        return None
    return None


def process_row(s, row):
    """Process one row. Returns (new_geo, new_address, source_tag) or (None, None, None)."""
    # Only target IP-traced sources
    if len(row) <= 33:
        return None
    notes = row[33] if len(row) > 33 else ''
    if 'source=insecam_dump' not in notes and 'source=full-reprobe' not in notes:
        return None
    # Skip if already has EXIF or HTML-scrape source
    if len(row) > 25 and row[25] in ('tier2:html', 'tier3:exif'):
        return None

    stream_url = row[3]
    if not stream_url:
        return None

    candidates = base_url(stream_url)
    for url in candidates:
        html = fetch_url(s, url)
        if not html:
            continue
        info = extract_from_html(html)
        if info['lat'] or info['city'] or info['address']:
            return info
    return None


def main():
    log('[init] starting HTML extractor (Tier 2)')
    s = session()

    # Read CSV
    with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    header = rows[0]
    log(f'[init] {len(rows)-1} rows, {len(header)} cols')

    cols = {h: i for i, h in enumerate(header)}
    LAT = cols['lat']; LON = cols['lon']
    CCY = cols['city']; CREG = cols['region']
    CADDR = cols.get('address', None)
    CGEO = cols.get('geo_source', None)
    # Re-resolve in case column order changed since writing this
    if 'lat' not in cols: LAT = None  # header error
    if 'geo_source' not in cols: CGEO = None

    # Build list of (row_idx, row) to process
    targets = []
    for i, r in enumerate(rows[1:], start=1):
        if len(r) <= 33:
            continue
        notes = r[33]
        if 'source=insecam_dump' not in notes and 'source=full-reprobe' not in notes:
            continue
        if CGEO is not None and len(r) > CGEO and r[CGEO] in ('tier2:html', 'tier3:exif'):
            continue
        targets.append((i, r))
    log(f'[plan] {len(targets)} rows to scrape')

    # Process in parallel
    def process(t):
        idx, row = t
        return idx, process_row(s, row)

    updated = 0
    done = 0
    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(process, t): t for t in targets}
        for f in as_completed(futures):
            done += 1
            try:
                idx, info = f.result()
            except Exception:
                continue
            if not info:
                continue
            r = rows[idx]
            changed = False
            if info['lat'] and info['lon']:
                # Update only if new lat/lon differs significantly from IP-traced (sanity check)
                try:
                    old_lat = float(r[LAT]) if r[LAT] else 0
                    old_lon = float(r[LON]) if r[LON] else 0
                    new_lat = float(info['lat'])
                    new_lon = float(info['lon'])
                    # Distance check: if new is <50km from old IP trace, accept
                    # For now accept any new that has positive lat
                    r[LAT] = str(new_lat); r[LON] = str(new_lon)
                    changed = True
                except ValueError:
                    pass
            if info['city'] and (not r[CCY] or len(r[CCY]) < len(info['city'])):
                r[CCY] = info['city'][:80]; changed = True
            if info['region'] and (not r[CREG] or len(r[CREG]) < len(info['region'])):
                r[CREG] = info['region'][:80]; changed = True
            if info['address'] and CADDR is not None and (not r[CADDR] or len(r[CADDR]) < len(info['address'])):
                r[CADDR] = info['address'][:200]; changed = True
            if changed:
                if CGEO is not None:
                    src_tags = ','.join(info.get('raw', ['tier2:html']))
                    r[CGEO] = f'tier2:{src_tags}'[:200]
                updated += 1
            if done % 50 == 0:
                log(f'  progress {done}/{len(targets)} updated={updated}')
                # checkpoint save
                tmp = CSV_PATH + '.tmp'
                with open(tmp, 'w', encoding='utf-8', newline='') as f:
                    w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
                    for rr in rows:
                        w.writerow(rr)
                os.replace(tmp, CSV_PATH)
    log(f'[done] updated {updated} rows')
    # Final save
    tmp = CSV_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
        for r in rows:
            w.writerow(r)
    os.replace(tmp, CSV_PATH)


if __name__ == '__main__':
    main()
