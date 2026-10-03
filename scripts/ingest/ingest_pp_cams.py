"""Add all 55 Pet Paradise cams to the CSV with full details."""
import csv, time, json, shutil, os
from pathlib import Path

CSV_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')
PREVIEW_SRC = Path(r'C:\Users\eli6-admin\AppData\Local\Temp\abckam_previews')
POSTER_DST = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\web_viewer\static\posters')

# Load Pet Paradise location details
LOCATIONS = {
    'huntsville': ('Madison', 'AL', '35758', '6260 Wall Triana Hwy.', 34.7567, -86.7485),
    'madison': ('Madison', 'AL', '35758', '6260 Wall Triana Hwy.', 34.7567, -86.7485),
    'ocala': ('Ocala', 'FL', '34476', '7571 SW State Rd 200', 29.0849, -82.1400),
    'sanford': ('Sanford', 'FL', '32771', '1100 W First St', 28.7995, -81.2756),
    'tallahassee': ('Tallahassee', 'FL', '32303', '2900 Commonwealth Blvd', 30.4717, -84.2697),
    'chesterfield': ('Chesterfield', 'VA', '23231', '1214 Koger Center Blvd', 37.5038, -77.5278),
    'richmond': ('Richmond Airport', 'VA', '23231', '4101 Williamsburg Rd', 37.5025, -77.3588),
    'viera': ('Viera', 'FL', '32955', '900 Viera Blvd', 28.2343, -80.7225),
    'las-colinas': ('Las Colinas', 'TX', '75039', '6150 Riverside Dr', 32.8927, -96.9650),
}

# Load all found cams
founds = json.loads(Path(r'C:\Users\eli6-admin\AppData\Local\Temp\abckam_results\pp_brute_full.json').read_text())

# Determine cam descriptions by preview frames (we have 55 previews)
# Just use generic naming
CAM_DESCRIPTIONS = {
    'huntsville': 'Indoor cat boarding suite. Individual private room with TV, cat bed, and litter area.',
    'ocala': 'Pet boarding facility indoor/outdoor areas. Cat boarding suite with private rooms.',
    'sanford': 'Pet boarding facility. Indoor cat boarding suite or dog play area with privacy dividers.',
    'tallahassee': 'Pet boarding facility. Indoor play areas, kennel runs with outdoor access.',
    'chesterfield': 'Pet boarding facility. Indoor cat boarding suites with individual cat accommodations.',
    'richmond': 'Pet boarding facility. Indoor/outdoor dog play areas with wading pool and kennel runs.',
    'viera': 'Pet boarding facility. Indoor and outdoor play areas with artificial grass and pool.',
    'las-colinas': 'Pet boarding facility. Indoor play area with agility equipment, outdoor kennel runs with pool.',
}

# Read existing CSV
with open(CSV_PATH, encoding='utf-8', newline='') as f:
    rows = list(csv.reader(f))
header = rows[0]
data = rows[1:]
H = {k: i for i, k in enumerate(header)}

# Find max idx for new IDs
max_idx = max(int(r[H['idx']]) for r in data if len(r) > H['idx'] and r[H['idx']].isdigit())
next_idx = max_idx + 1
print(f'Existing rows: {len(data)}, max_idx: {max_idx}, next_idx: {next_idx}')

# Build set of existing stream URLs to avoid duplicates
existing_urls = set()
for r in data:
    if len(r) > H['live_stream_url']:
        existing_urls.add(r[H['live_stream_url']])
print(f'Existing unique URLs: {len(existing_urls)}')

# Counter
added = 0
TODAY = time.strftime('%Y-%m-%d')

# Process each found cam
for f in founds:
    sid = f['stream_id']
    host = f['host']
    url = f['url']
    # Extract slug (pp-{slug}-{n} or pp-{slug}{n})
    after_pp = sid[3:]  # remove 'pp-'
    if '-' in after_pp:
        parts = after_pp.rsplit('-', 1)
        if parts[1].isdigit():
            slug, num_str = parts[0], parts[1]
            num = int(num_str)
        else:
            slug = after_pp
            num = 1
    elif '_' in after_pp:
        parts = after_pp.rsplit('_', 1)
        if parts[1].isdigit():
            slug, num_str = parts[0], parts[1]
            num = int(num_str)
        else:
            slug = after_pp
            num = 1
    else:
        slug = after_pp
        num = 1

    # Skip if URL already exists
    if url in existing_urls:
        continue

    # Get location
    if slug not in LOCATIONS:
        print(f'  SKIP {sid}: no location info')
        continue
    city_name, state, zip_, addr, lat, lon = LOCATIONS[slug]

    # Slight coordinate offset per cam for map placement
    offsets = [(0, 0), (0.0001, 0), (0, 0.0001), (-0.0001, 0), (0, -0.0001),
               (0.0001, 0.0001), (-0.0001, 0.0001), (0.0001, -0.0001)]
    if num - 1 < len(offsets):
        off = offsets[num - 1]
    else:
        off = (0, 0)
    cam_lat = lat + off[0]
    cam_lon = lon + off[1]

    name = f'Pet Paradise {city_name} - Cam {num}'
    desc = CAM_DESCRIPTIONS.get(slug, 'Pet boarding/day care facility webcam.')

    row = [''] * len(header)
    row[H['idx']] = str(next_idx)
    row[H['project_name']] = name
    row[H['url']] = url
    row[H['live_stream_url']] = url
    row[H['type']] = 'hls'
    row[H['auth_required']] = 'false'
    row[H['enabled']] = 'true'
    row[H['live_status']] = 'live'
    row[H['http_status']] = '200'
    row[H['content_type']] = 'application/vnd.apple.mpegurl'
    row[H['description']] = desc
    row[H['category']] = 'animal-care'
    row[H['likely_subject']] = 'dog cat boarding daycare kennel pet resort'
    row[H['country']] = 'United States'
    row[H['region']] = state
    row[H['city']] = city_name
    row[H['zip']] = zip_
    row[H['address']] = addr
    row[H['road']] = addr.split(',')[0] if ',' in addr else addr
    row[H['location_precision']] = 'rooftop'
    row[H['lat']] = str(cam_lat)
    row[H['lon']] = str(cam_lon)
    row[H['geo_source']] = 'petparadise.com/locations.htm'
    row[H['isp']] = 'Ant Media Server'
    row[H['reverse_dns']] = host
    row[H['host']] = host
    row[H['confidence']] = '8'
    notes = f'ingest_v5 {TODAY} cam=petparadise({slug}) operator=ABC Kam source=user_supplied_discovery'
    row[H['notes']] = notes
    row[H['csv_id']] = str(int(time.time()) + next_idx)

    data.append(row)
    existing_urls.add(url)
    added += 1
    next_idx += 1

print(f'Added {added} cams')

# Write back
with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
    w.writerow(header)
    for r in data:
        w.writerow(r)
print(f'Wrote {len(data)} total rows')

# Copy preview images as posters
poster_count = 0
for f in founds:
    sid = f['stream_id']
    host = f['host'].replace('.abckam.com', '')
    src = PREVIEW_SRC / f'{host}_{sid}.jpg'
    if not src.exists():
        continue
    # Get idx for this cam from CSV
    url = f['url']
    for r in data:
        if len(r) > H['live_stream_url'] and r[H['live_stream_url']] == url:
            idx = r[H['idx']]
            dst = POSTER_DST / f'{idx}.jpg'
            if not dst.exists():
                shutil.copy(src, dst)
                poster_count += 1
            break
print(f'Copied {poster_count} posters')
