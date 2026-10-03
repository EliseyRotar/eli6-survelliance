"""
PHASE 4: Argus Cleanup - Process all 59,938 '(argus)' cams.

For each argus cam:
1. Parse notes for argus_id and source prefix
2. Look up enrichment per source (URL pattern, public catalogs)
3. Reverse geocode for via/road (where possible)
4. Strip '(argus)' from name
5. Set location_precision field

This is a LARGE operation on 60k rows. To stay within 1 hour, we:
- Don't re-geocode (too slow at 1 req/sec)
- Use URL/path pattern analysis for name enrichment
- Use batch operations (no per-row disk I/O)
"""
import csv
import re
from pathlib import Path
from collections import defaultdict, Counter

CSV_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')

# Patterns to extract from URL or notes
# Each: (url_pattern, name_pattern, source_label)
URL_PATTERNS = [
    # Japan MLIT river cams (cam.river.go.jp)
    (r'cam\.river\.go\.jp.*?/(\d+)/image\.jpg', 'Japan MLIT River Cam {1}'),
    (r'cam\.river\.go\.jp/(\d+)', 'Japan MLIT River Cam {1}'),
    # State DOTs
    (r'wzmedia\.dot\.ca\.gov/D(\d+)/([^/]+)', 'Caltrans D{0} - {1}'),
    (r'511mn\.org/.*?/(\d+)', 'MN DOT 511 Cam {1}'),
    (r'video2\.iowadot\.gov:8888/(\w+)/(\w+)', 'Iowa DOT {0} {1}'),
    (r'511ny\.org/map/Cctv/(\d+)', 'NY 511 Cctv {1}'),
    (r'prod-ut\.ibi511\.com', 'Utah DOT 511 Cam'),
    (r'511\.alaska\.gov/map/Cctv/(\d+)', 'Alaska DOT Cam {1}'),
    (r'cctv-ss(\d+)\.thb\.gov\.tw:443/(.+)', 'Taiwan Freeway {0} {1}'),
    (r'cctvs\.freeway\.gov\.tw.*camera=(\d+)', 'Taiwan Freeway Cam {1}'),
    (r'cctv\.travelmidwest\.com/snapshots/([A-Z]+-[A-Z0-9]+_[A-Z]+_.*?)\.jpg', 'IL DOT Travelmidwest {1}'),
    (r'nysmesonet\.org/mesonet/current/(\d+)', 'NY State Mesonet {1}'),
    # Windy cams
    (r'imgproxy\.windy\.com/_/full/plain/current/(\d+)/original\.jpg', 'Windy Webcam {1}'),
    (r'images-webcams\.windy\.com/\d+/(\d+)/current/.*\.jpg', 'Windy Webcam {1}'),
    # City of Albuquerque
    (r'cabsweb\.cabq\.gov', 'Albuquerque City Cam'),
    # Various city-specific
    (r'images/(\w+)_(\d+)\.jpg', '{0} cam {1}'),
]

# Source classification from argus_id
SOURCE_REGEX = re.compile(r'argus_id=opencctv_([a-z0-9_]+?)(?:[_-]|$)')
SOURCE_PRETTY = {
    'windy': 'Windy Webcam',
    'windy_providers': 'Windy Webcam',
    'cam_river': 'Japan MLIT River Cam',
    'arcgis': 'State DOT 511',
    's511': 'State DOT 511',
    'state511': 'State DOT 511',
    'autostrade': 'Italy Autostrade',
    'Skyline': 'NYSDOT Skyline HLS',
    'NYSDOT': 'NYSDOT',
    'nysdot': 'NYSDOT',
    'dgt': 'Spain DGT',
    'etraffic': 'Spain DGT',
    'panomax': 'Panomax',
    'feratel': 'Feratel Südtirol',
    'opendatahub': 'Feratel Südtirol',
    'i_traffic': 'i-Traffic South Africa',
    'digitraffic': 'Finland Digitraffic',
    'weathercam_digitraffic': 'Finland Digitraffic',
    'webcamera_pl': 'Poland Webcamera',
    'pl_webcamera': 'Poland Webcamera',
    'alertcalifornia': 'ALERTCalifornia',
    'phenocam': 'NEON Phenocam',
    'jogjaprov': 'Indonesia Yogyakarta',
    'catalonia': 'Catalonia Traffic',
    'chmi': 'Czech Hydromet',
    'ndbc': 'NOAA NDBC Buoy',
    'nexco': 'Japan NEXCO',
    'tenerife': 'Tenerife Traffic',
    'quebec': 'Quebec 511',
    'sanluis': 'San Luis Cam',
    'travelmidwest': 'IL Travelmidwest',
    'atv': 'Japan ATV Weather',
    'kfa': 'KFA Weather',
    'nysm': 'NY State Mesonet',
    'cityof': 'City Cam',
    'ifrc': 'IFRC Cam',
    'sk_kukaj': 'Slovakia Webcam',
    'barcelona': 'Barcelona Cam',
    'csic': 'CSIC Research Cam',
    'geiger': 'Geiger Counter Cam',
    'ame': 'Ame Cam',
    'gecam': 'GECAM',
    'mteb': 'MTEB Cam',
    'idph': 'IDPH',
    'puertos': 'Ports Cam',
    'fomento': 'Fomento Cam',
    'ria': 'RIA Cam',
    'gnss': 'GNSS Cam',
    'mma': 'MMA Cam',
    'trafikverket': 'Sweden Trafikverket',
    'utb': 'UTB',
    'video': 'Video Cam',
    'webcam': 'Webcam',
    'webcams': 'Webcam',
    'trafficcams': 'Traffic Cam',
    'atv': 'Japan ATV Weather',
    'cabq': 'Albuquerque City Cam',
    'widgets': 'Widgets Cam',
    'wowza': 'Wowza',
    'park': 'Park Cam',
    'vail': 'Vail Resort Cam',
    'weather': 'Weather Cam',
    'trafficland': 'Trafficland',
    'trafficcam': 'Traffic Cam',
    'trafiko': 'Trafiko',
    'trafik': 'Trafik',
    'tntech': 'TN Tech',
    'transports': 'Transports',
    'unhcr': 'UNHCR',
    'usgs': 'USGS',
    'odc': 'ODC',
    'dodot': 'DC DOT',
    'maryland': 'Maryland DOT',
    'maine': 'Maine DOT',
    'virginia': 'Virginia DOT',
    'nvroads': 'Nevada DOT',
    'iowa': 'Iowa DOT',
    'ia': 'Iowa DOT',
    'i-traffic': 'i-Traffic ZA',
    'autostrade': 'Italy Autostrade',
    'tfc': 'TFC',
    'tfr': 'TFR',
    'tfl': 'TFL',
    'rta': 'RTA',
    'fdot': 'Florida DOT',
    'ddot': 'Delaware DOT',
    'caltrans': 'Caltrans',
    'mndot': 'MN DOT',
    'illinois': 'Illinois DOT',
    'inrix': 'INRIX',
    'iteris': 'Iteris',
    'waze': 'Waze',
    'public': 'Public Cam',
    'open': 'Open Cam',
    'cctv': 'CCTV',
    'image': 'Image Cam',
    'iframe': 'Iframe Cam',
    'widgets': 'Widgets',
    'river': 'River Cam',
    'traffic': 'Traffic Cam',
    'agency': 'Agency Cam',
    'cam': 'Cam',
    'web': 'Web Cam',
}

# URL-based patterns
URL_NAME_PATTERNS = [
    # Windy UUID - generate from ID, but lookup might give name
    (r'imgproxy\.windy\.com/_/full/plain/current/(\d+)/original\.jpg', 'Windy Webcam {0}'),
    (r'images-webcams\.windy\.com/\d+/(\d+)/current/.*\.jpg', 'Windy Webcam {0}'),
    # Caltrans D11
    (r'wzmedia\.dot\.ca\.gov/D(\d+)/([A-Z]\d+_[A-Z]+_\d+_(?:at|of|JNO|JSO|JWO|JEO|just\sN|just\sS|just\sE|just\sW|NB|SB|EB|WB)\b.*?)\.stream', 'Caltrans D{0} - {1}'),
    # Japan MLIT
    (r'cam\.river\.go\.jp/(\d+)/image\.jpg', 'Japan River Cam {0}'),
    (r'https?://([^/]+)/(\d+)/image\.jpg', '{0} Cam {1}'),
    # generic IMG_xxx
    (r'/IMG_(\d+)\.jpg', 'Cam {0}'),
    # numeric path
    (r'/(\d{4,})\.jpg$', 'Cam {0}'),
]

# State DOT URL-based name extraction
STATE_DOT_PATTERNS = [
    # wzmedia.dot.ca.gov - extract route+location from URL
    (r'D(\d+)/([A-Z]\d+)_([A-Z]+)_(\d+)_([^.]+)\.stream',
     r'Caltrans D\1 - \2 \3 MM\4 at \5'),
    # 511NY site patterns
    (r'511ny\.org/.*?/(\d+)\b', r'NY 511 Cam \1'),
    # Iowa DOT
    (r'video\d?\.iowadot\.gov:8888/(\w+)/([a-z]+\d+lb)', r'Iowa DOT \1 - \2'),
]

# 1) Read all rows
print("Reading CSV...")
with open(CSV_PATH, encoding='utf-8', newline='') as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = list(reader)

# Build header index
H = {k: i for i, k in enumerate(header)}
print(f"Total rows: {len(rows)}")
print(f"Header has {len(header)} cols")

# 2) Find all (argus) rows
argus_rows = []
for ri, row in enumerate(rows):
    if len(row) > H['project_name'] and '(argus)' in row[H['project_name']]:
        argus_rows.append((ri, row))

print(f"Argus rows: {len(argus_rows)}")

# 3) Process each argus row: strip (argus), classify, enrich
print("Processing argus rows...")
updated = 0
for ri, row in argus_rows:
    if len(row) != len(header):
        continue
    name = row[H['project_name']]
    notes = row[H['notes']] if len(row) > H['notes'] else ''

    # Strip ' (argus)' suffix
    new_name = re.sub(r'\s*\(argus\)\s*$', '', name).strip()
    if not new_name:
        new_name = 'Webcam'

    # Classify source from notes
    source = 'unknown'
    m = SOURCE_REGEX.search(notes)
    if m:
        source = m.group(1)
    # also check URL for hints
    url = row[H['url']] or ''
    live = row[H['live_stream_url']] or ''

    # Try URL patterns to enrich the name
    for pattern, replacement in URL_NAME_PATTERNS:
        m = re.search(pattern, live or url)
        if m:
            new_name = re.sub(pattern, replacement, live or url)
            new_name = re.sub(r'[^A-Za-z0-9\s\-_:.]+', ' ', new_name).strip()[:120]
            break

    # Better naming based on host + URL pattern
    if new_name in ('Cam', 'Webcam') or len(new_name) < 5:
        host = row[H['host']] if len(row) > H['host'] else ''
        # Try to extract city/region from URL path
        city_m = re.search(r'/(cam|image|upload|video|pic|jpg|png|img|stream)/([^/.]+)\.', live or url)
        if city_m:
            new_name = f"{host or 'Webcam'} - {city_m.group(2).replace('-', ' ').title()}"
        else:
            new_name = f"{host or 'Webcam'} Webcam"

    # Set brand and model based on source
    if source in SOURCE_PRETTY:
        brand = SOURCE_PRETTY[source]
    else:
        brand = f"Public Cam ({source})"
    model_str = source.upper() if source != 'unknown' else 'Unknown'

    # Set location_precision
    # We can use 'approximate_from_region' or 'host_default' based on the source quality
    # But we don't have specific lat/lng analysis here - just set to 'low' (will be upgraded later)
    lat = row[H['lat']] if len(row) > H['lat'] else ''
    lon = row[H['lon']] if len(row) > H['lon'] else ''
    # If lat/lon are default placeholders, mark as host_default; else approximate
    try:
        lat_f = float(lat) if lat else 0
        lon_f = float(lon) if lon else 0
    except:
        lat_f = lon_f = 0
    if lat_f == 0 and lon_f == 0:
        precision = 'no_coords'
    elif (lat_f, lon_f) in [(36.57, -118.09), (40.5023, -0.1908), (43.793, 142.28), (22.248, 114.15), (47.428, 11.695), (50.383, 11.885)]:
        precision = 'host_default'  # These are the argus default coords
    else:
        precision = 'approximate_from_region'

    # Update row in place
    row[H['project_name']] = new_name
    row[H['brand']] = brand
    row[H['model']] = model_str
    row[H['location_precision']] = precision
    # Remove (argus) from org field too if present
    if len(row) > H['org']:
        org = row[H['org']] or ''
        if '(argus)' in org.lower():
            row[H['org']] = re.sub(r'\s*\(argus\)\s*', '', org, flags=re.I).strip()
    # Update notes to record argus cleanup
    if len(row) > H['notes']:
        existing_notes = row[H['notes']] or ''
        if 'argus_cleanup_v1' not in existing_notes:
            row[H['notes']] = (existing_notes + ' | argus_cleanup_v1').strip()
    updated += 1

print(f"Updated {updated} argus rows")
print(f"Writing CSV...")

# Write back
with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
print("Done.")
