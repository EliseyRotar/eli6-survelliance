"""
argus_cleanup_v5.py — pack everything useful into the project_name.

Strategy: when a cam has a generic/placeholder name, build a rich name from:
  [road/highway] · [city, region, country] · [operator] · [host short] · [cam id]

If we have NO real location and NO road, fall back to operator + cam id.

Operator comes from HOST_OPERATOR lookup or derived from host subdomain.
Cam ID is extracted from URL via regex.

Also: even for GOOD existing names, append the location if it's missing
and we have it. This makes the dashboard MUCH more informative.

Order of bits (most-to-least specific first):
  1. Road / highway designation  (e.g. "I-5 NB", "SR-99", "A406")
  2. City (or region if no city)
  3. Country (only if not derivable from operator)
  4. Operator (e.g. "Caltrans", "Iowa DOT", "Windy Webcam")
  5. Cam identifier (numeric ID or short slug)
"""
import csv
import re
import sys
from pathlib import Path

# Force UTF-8 stdout so non-ASCII chars don't break Windows console
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

CSV_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')

HOST_OPERATOR = {
    'cameras.alertcalifornia.org': 'ALERTCalifornia',
    'images-webcams.windy.com': 'Windy',
    'imgproxy.windy.com': 'Windy',
    'webcams.opensnow.com': 'OpenSnow',
    'www.atv.jp': 'Japan ATV Weather',
    'cam.river.go.jp': 'Japan MLIT River',
    'etraffic.dgt.es': 'Spain DGT',
    'wzmedia.dot.ca.gov': 'Caltrans',
    'www.houstontranstar.org': 'Houston TranStar',
    'prod-ut.ibi511.com': 'NY 511',
    'www.nvroads.com': 'Nevada DOT',
    'tdcctv.data.one.gov.hk': 'Hong Kong TDCCTV',
    'video.dot.state.mn.us': 'Minnesota DOT',
    'video.auth1.iol.pt': 'Portugal Beachcam',
    'video.auth2.iol.pt': 'Portugal Beachcam',
    'video.auth3.iol.pt': 'Portugal Beachcam',
    'video.autostrade.it': 'Autostrade per l\'Italia',
    'atmsqf.iowadot.gov': 'Iowa DOT',
    'video1.iowadot.gov': 'Iowa DOT',
    'video2.iowadot.gov': 'Iowa DOT',
    'video3.iowadot.gov': 'Iowa DOT',
    'video4.iowadot.gov': 'Iowa DOT',
    'www.netraveldata.co.uk': 'UK NE Travel',
    'imageserver.webcamera.pl': 'Poland Webcamera',
    'weathercam.digitraffic.fi': 'Finland Digitraffic',
    'phenocam.nau.edu': 'NEON Phenocam',
    'www.511ny.org': 'NY 511',
    'informo.madrid.es': 'Madrid Informo',
    'i-traffic.co.za': 'i-Traffic South Africa',
    'micamerasimages.net': 'Micam Images',
    'cctv.jogjaprov.go.id': 'Jogjaprov Indonesia',
    'public.carsprogram.org': 'CARSPROGRAM',
    'wtvpict.feratel.com': 'Feratel',
    'wtvthmb.feratel.com': 'Feratel',
    'map.bayerninfo.de': 'Bayern Info',
    '511on.ca': 'Ontario 511',
    'www.newengland511.org': 'New England 511',
    'cctv.divvysign.com': 'DivvySign',
    'vibes.dot.ca.gov': 'Caltrans Vibes',
    'www.skylinewebcams.com': 'Skyline Webcams',
    'video.kamere.com': 'Kamere',
    'api.wetcentrally.com': 'WetCentrally',
    'cam.creme.io': 'Creme.io',
    'vdo.telecores.com': 'Telecores',
    'cdn.openuni.io': 'OpenUni',
    'livecam.dandenong.vic.gov.au': 'Dandenong Council',
    'rivercam.niwa.co.nz': 'NIWA Rivercam',
    'mountainwatch.com': 'Mountain Watch',
    'rthkweb.mediahosting.app': 'RTHK',
    'snow.cusalpin.eu': 'Cusalpin Snow',
    'api.yr.no': 'YR Weather',
    'media-cdn.mgm-corp.com': 'MGM Corp',
    # New mappings
    'mct.gencat.cat': 'MeteoCat',
    'bcn.cat': 'Barcelona',
    'cdn.goakamai.org': 'GoAkamai',
    'mms.iptv.unideb.hu': 'Debrecen Univ',
    'www.awi.de': 'AWI Alfred Wegener',
    'www.belgianrail.be': 'Belgian Rail',
    'cdn.branasgruppen.se': 'Branas',
}

# ID extraction patterns
ID_PATTERNS = [
    r'/public-camera-data/([A-Za-z][A-Za-z0-9_-]+?)/latest',
    r'/public-camera-data/([A-Za-z][A-Za-z0-9_-]+?)/',
    r'/Axis[-_]([A-Za-z0-9][A-Za-z0-9_-]+)',
    r'/Public/RestAreas/([A-Z][A-Z0-9-]+)',
    r'/Public/(?:Highways|Intersections|Ramps|Cameras)/([A-Z][A-Z0-9-]+)',
    r'/video-frames/(dt\d+/[0-9a-f]{8})',
    r'/video-frames/(dt\d+)',
    r'/snapshots/Public/\w+/([A-Z][A-Z0-9-]+)',
    r'/map/Cctv/(\d+)',
    r'/cctv/(\d+)',
    r'/webcam/([A-Za-z0-9-]+)',
    r'/images/([A-Z][A-Z0-9_-]+?)\.',
    r'/cam[-_]([A-Za-z0-9][A-Za-z0-9_-]+?)\.',
    r'/chan[-_](\w+)/',
    r'/chan[-_](\w+)\.',
    r'cctv[-_](\d+)\.',
    r'cam[_=](\d+)',
    r'cam[-_](\d+)\.jpg',
    r'camera[-_](\d+)\.',
    r'/(\d+)/image\.jpg',
    r'/(\d+)/latest\.jpg',
    r'/(\d{4,})\.jpg',
    r'images/(\d+)\.jpg',
    r'live/(\d{4,})',
    r'/cam[_-]?(\d+)',
    r'idx[=](\d+)',
    r'/([A-Z0-9]{2,}[_-][A-Z][_-]?\d+)\.jpg',
    r'/([A-Z]\d+_?[A-Z]?_\d+)\.jpg',
]


def operator_from_host(host):
    if not host:
        return ''
    host = host.lower()
    if host in HOST_OPERATOR:
        return HOST_OPERATOR[host]
    base = re.sub(r'^www\.', '', host)
    parts = base.split('.')
    if len(parts) >= 2:
        sub = parts[0]
        # Skip generic first-level domains like cdn, www
        if sub in ('cam', 'cams', 'video', 'image', 'images', 'cctv', 'snapshot', 'www', 'cdn'):
            sub = parts[1] if len(parts) > 1 else sub
        # If the next part is also generic, try the parent domain (parts[-2])
        if sub in ('cam', 'cams', 'video', 'image', 'images', 'cctv', 'snapshot', 'www', 'cdn') and len(parts) > 1:
            sub = parts[-2]
        # Filter junk suffixes
        sub = re.sub(r'\.(com|net|org|gov|io|eu|co\.uk)$', '', sub)
        # Only return if it's at least 3 chars and looks meaningful
        if len(sub) >= 3 and sub.isalpha():
            return sub.title()
    return ''


def extract_cam_id(url):
    if not url:
        return None
    for pat in ID_PATTERNS:
        m = re.search(pat, url, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def is_generic(name):
    if not name:
        return True
    n = name.strip()
    if len(n) < 4:
        return True
    patterns = [
        r'^[a-z0-9-]+\s+webcam$', r'^[a-z0-9-]+\s+camera$',
        r'^cameras?\s+webcam$', r'^videos?\s+webcam$',
        r'^cam[_a-z0-9-]+$', r'^cctv[_a-z0-9-]*$',
        r'^https?:', r'^\d+\.jpg$', r'\.m3u8$', r'^rtsp:',
    ]
    for p in patterns:
        if re.match(p, n, re.I):
            return True
    return False


def has_location(parts):
    """True if any of road/city/region/country is filled."""
    return any(parts.get(k) for k in ('road', 'city', 'region', 'country'))


def clean_dupes(s):
    """Strip duplicate tokens from a bullet-separated string."""
    parts = [p.strip() for p in s.split('·') if p.strip()]
    seen = set()
    out = []
    for p in parts:
        # Collapse case-insensitive dupes
        k = p.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(p)
    return ' · '.join(out)


def build_name(row, idx):
    """Build a rich project_name for this cam row.

    Returns the new name, or None if no useful change is possible.
    """
    H = ROW_HEADER
    road = (row[H['road']] if H['road'] < len(row) else '').strip()
    city = (row[H['city']] if H['city'] < len(row) else '').strip()
    region = (row[H['region']] if H['region'] < len(row) else '').strip()
    country = (row[H['country']] if H['country'] < len(row) else '').strip()
    host = (row[H['host']] if H['host'] < len(row) else '').strip()
    url = (row[H['url']] if H['url'] < len(row) else '').strip()
    live = (row[H['live_stream_url']] if H['live_stream_url'] < len(row) else '').strip()
    city_precision = (row[H['location_precision']] if H['location_precision'] < len(row) else '').strip()

    operator = operator_from_host(host)
    cam_id = extract_cam_id(url) or extract_cam_id(live)

    # Build a list of meaningful tokens, then bullet-join
    bits = []

    # 1. Road/highway: prefer over everything if present and looks like a real designation
    if road:
        # Cleanup: "I-5" stays, "(I-5)" ok too
        # Some roads have weird chars - keep them but trim spaces
        road_clean = re.sub(r'\s+', ' ', road).strip()
        if len(road_clean) <= 60 and (any(c.isdigit() for c in road_clean) or 'highway' in road_clean.lower()):
            bits.append(road_clean)

    # 2. Location: prefer city+country together
    loc = []
    if city and city != 'nan':
        loc.append(city)
    if region and region != city and region != 'nan':
        loc.append(region)
    if country and country != 'nan':
        # Only add country if there's something meaningful
        if len(loc) < 2:  # don't add if we already have city+region
            loc.append(country)
    if loc:
        bits.append(', '.join(loc))

    # 3. Operator
    if operator:
        bits.append(operator)

    # 4. Cam ID
    if cam_id:
        bits.append(f'#{cam_id}')
    else:
        bits.append(f'#{idx}')

    if not any(bits[1:]):  # no meaningful info beyond idx?
        return None

    new_name = ' · '.join(bits)

    # Cap length
    if len(new_name) > 180:
        new_name = new_name[:177] + '...'

    return new_name


def main():
    global ROW_HEADER
    print(f'Reading {CSV_PATH}')
    with open(CSV_PATH, encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    header = rows[0]
    data = rows[1:]
    ROW_HEADER = {k: i for i, k in enumerate(header)}

    if 'road' not in ROW_HEADER or 'location_precision' not in ROW_HEADER:
        print('ERROR: CSV missing road or location_precision column')
        return

    updated = 0
    skipped_no_data = 0
    sample = []
    for i, row in enumerate(data):
        if len(row) != len(header):
            continue
        idx = row[ROW_HEADER['idx']] if ROW_HEADER['idx'] < len(row) else '?'
        name = row[ROW_HEADER['project_name']] if ROW_HEADER['project_name'] < len(row) else ''
        if not is_generic(name):
            continue
        new_name = build_name(row, idx)
        if not new_name:
            skipped_no_data += 1
            continue
        if new_name == name:
            continue
        # Dedup near-duplicates within new_name
        new_name = clean_dupes(new_name)
        row[ROW_HEADER['project_name']] = new_name
        notes_idx = ROW_HEADER.get('notes', -1)
        if notes_idx >= 0:
            existing = row[notes_idx] if notes_idx < len(row) else ''
            tag = 'cleanup_v5'
            if tag not in existing:
                row[notes_idx] = (existing + ' ' + tag).strip()[:200]
        updated += 1
        if len(sample) < 30:
            sample.append((idx, name, new_name))

    print(f'Updated {updated} generic names ({skipped_no_data} skipped due to no useful data)')
    if sample:
        print('\nSample changes:')
        for idx, old, new in sample:
            try:
                print(f'  idx={idx}: "{old}" -> "{new}"')
            except UnicodeEncodeError:
                # Print repr to avoid console encoding issues with Polish/Czech chars
                print(f'  idx={idx}: {repr(old)} -> {repr(new)}')

    if not updated:
        return
    print(f'\nWriting back to {CSV_PATH}')
    with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(header)
        for row in data:
            writer.writerow(row)
    print('Done.')


if __name__ == '__main__':
    main()
