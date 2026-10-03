"""Ingest all ALERTCalifornia cams from the master GeoJSON into our DB.
Maps to controllable_Webcams.csv schema:
- idx (next free)
- live_stream_url = https://cameras.alertcalifornia.org/public-camera-data/{slug}/latest-frame.jpg
- host = cameras.alertcalifornia.org
- project_name = "{name} · ALERTCalifornia · #{slug}" (or just #{slug} if no name)
- city, region, country = from properties.state, properties.county, "United States"
- lat, lon = from coordinates [East, North, Elev]
- road = "ALERTCalifornia"
- location_precision = "exact" if has coords, else "region"
"""
import json, csv, sys
from pathlib import Path
import re

src = Path(r'C:\Users\eli6-admin\AppData\Local\Temp\ac_all_cameras-v3.json')
csv_path = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')

# Region codes → full names (USFS)
REGION_NAMES = {
    'HUU': 'Humboldt Unit', 'SCU': 'Santa Clara Unit', 'LMU': 'La Madre Unit',
    'LNU': 'Los Padres Unit', 'BEU': 'Ben Lomond Unit', 'SDU': 'San Diego Unit',
    'CZU': 'CZU Unit', 'MRN': 'Marin Unit', 'FKU': 'Fresno-Kings Unit',
    'SLU': 'San Luis Unit', 'SBC': 'Santa Barbara County', 'SKU': 'Sequoia Unit',
    'TGU': 'Tehama-Glenn Unit', 'VNC': 'Ventura County', 'AEU': 'Amador-El Dorado Unit',
    'BTU': 'Butte Unit', 'NEU': 'Nevada-Yuba-Placer Unit', 'SHU': 'Shasta-Trinity Unit',
    'TCU': 'Tuolumne-Calaveras Unit', 'MEU': 'Mendocino Unit', 'KRN': 'Kern County',
    'MMU': 'Madera-Mariposa Unit', 'TUU': 'Tulare Unit', 'RDR': 'Riverside Unit',
    'ORC': 'Orange County', 'IMP': 'Imperial Unit', 'SBR': 'San Bernardino Unit',
}

with src.open(encoding='utf-8') as f:
    j = json.load(f)
features = j['features']
print(f'Features: {len(features)}')

# Read existing CSV
with csv_path.open(encoding='utf-8', newline='') as f:
    rdr = csv.DictReader(f)
    fieldnames = rdr.fieldnames
    print(f'CSV has {len(fieldnames)} cols: {fieldnames[:10]}...')
    rows = list(rdr)
print(f'Existing rows: {len(rows)}')

# Existing AC slugs (so we don't duplicate)
existing_ac_slugs = set()
for r in rows:
    if 'cameras.alertcalifornia.org' in r.get('host', ''):
        m = re.search(r'/public-camera-data/([^/]+)/', r.get('live_stream_url',''))
        if m:
            existing_ac_slugs.add(m.group(1))
print(f'Existing AC slugs: {len(existing_ac_slugs)}')

# Determine next idx
max_idx = max((int(r['idx']) for r in rows if r.get('idx','').isdigit()), default=0)
print(f'Max idx: {max_idx}')

# Build new rows
new_rows = []
skipped = []
for feat in features:
    p = feat['properties']
    slug = p.get('id')
    if not slug or slug in existing_ac_slugs:
        skipped.append(slug or 'N/A')
        continue

    coords = feat['geometry']['coordinates']
    lon, lat = (coords[0], coords[1]) if coords[0] is not None else ('', '')
    if isinstance(lon, str) or isinstance(lat, str):
        # some coords might be string
        try:
            lon = float(lon); lat = float(lat)
        except:
            lon = lat = ''

    state = p.get('state', '') or ''
    county = p.get('county', '') or ''
    region_code = p.get('region', '') or ''
    region_name = REGION_NAMES.get(region_code, region_code)
    sponsor = p.get('sponsor', '') or ''
    isp = p.get('isp', '') or ''
    name = p.get('name', '') or ''

    # Use region_name as region in DB, county as city for precision
    if county:
        city = county
        region = region_name or state
    elif region_name:
        city = region_name
        region = state
    elif state:
        city = state
        region = ''
    else:
        city = ''
        region = ''

    # Project name: prefer real name, fallback to slug
    if name:
        proj_name = f'{name} · ALERTCalifornia · #{slug}'
    else:
        proj_name = f'#{slug}'

    # Road: ALERTCalifornia + sponsor if any
    road = 'ALERTCalifornia'
    if sponsor:
        road = f'ALERTCalifornia · {sponsor}'

    # Location precision
    if isinstance(lon, float) and isinstance(lat, float):
        loc_precision = 'exact'
    else:
        loc_precision = 'region'

    idx = str(max_idx + 1 + len(new_rows))
    live_url = f'https://cameras.alertcalifornia.org/public-camera-data/{slug}/latest-frame.jpg'

    row = {
        'idx': idx,
        'live_stream_url': live_url,
        'host': 'cameras.alertcalifornia.org',
        'project_name': proj_name,
        'city': city,
        'region': region,
        'country': 'United States',
        'lat': str(lat) if lat != '' else '',
        'lon': str(lon) if lon != '' else '',
        'road': road,
        'location_precision': loc_precision,
        'live_status': 'live',
        'isp': isp,
        'enabled': '1',
    }

    # Fill missing cols with ''
    for fn in fieldnames:
        if fn not in row:
            row[fn] = ''

    new_rows.append(row)

print(f'\nNew rows to add: {len(new_rows)}')
print(f'Skipped (duplicates): {len(skipped)}')

# Show sample
if new_rows:
    r0 = new_rows[0]
    print(f'\nSample new row:')
    for k in ['idx', 'project_name', 'city', 'region', 'country', 'lat', 'lon', 'live_stream_url', 'road']:
        v = r0.get(k, '')
        print(f'  {k}: {str(v)[:80]}')

# Save new rows to a separate CSV for review first
review_path = Path(r'C:\Users\eli6-admin\AppData\Local\Temp\ac_new_rows.csv')
with review_path.open('w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    for r in new_rows:
        w.writerow(r)
print(f'Saved {len(new_rows)} review rows to {review_path}')
