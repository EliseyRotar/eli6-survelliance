"""
Apply Nominatim geocoded names to argus cams (v4).
For each argus cam with lat/lon, look up Nominatim cache and use city/road info.
"""
import csv
import json
from pathlib import Path

CSV = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')
CACHE = Path(r'C:\Users\eli6-admin\AppData\Local\Temp\opencode\nominatim_cache.json')

if not CACHE.exists():
    print('No cache yet, skipping')
    import sys
    sys.exit(0)

with open(CACHE, encoding='utf-8') as f:
    cache = json.load(f)
print(f'Loaded {len(cache)} cached geocodes')

with open(CSV, encoding='utf-8', newline='') as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = list(reader)
H = {k: i for i, k in enumerate(header)}

# Find argus rows
updated = 0
for ri, row in enumerate(rows):
    if len(row) != len(header):
        continue
    notes = row[H['notes']] if len(row) > H['notes'] else ''
    if 'argus_cleanup_v1' not in notes:
        continue
    lat = row[H['lat']] if len(row) > H['lat'] else ''
    lon = row[H['lon']] if len(row) > H['lon'] else ''
    if not lat or not lon:
        continue
    try:
        lat_f = round(float(lat), 6)
        lon_f = round(float(lon), 6)
    except:
        continue
    key = f'{lat_f:.6f},{lon_f:.6f}'
    if key not in cache:
        # Try with 4 decimals
        key4 = f'{lat_f:.4f},{lon_f:.4f}'
        if key4 in cache:
            key = key4
        else:
            key3 = f'{lat_f:.3f},{lon_f:.3f}'
            if key3 in cache:
                key = key3
            else:
                continue
    info = cache[key]
    if not info or not isinstance(info, dict):
        continue
    addr = info.get('address', {}) if isinstance(info.get('address'), dict) else {}
    if not addr:
        # Top-level fields (alternative format)
        city = info.get('city') or info.get('town') or info.get('village') or info.get('hamlet') or info.get('suburb') or info.get('county') or ''
        county = info.get('county') or info.get('state') or ''
        country = info.get('country', '')
        road = info.get('road') or info.get('pedestrian') or info.get('footway') or info.get('path') or ''
    else:
        road = addr.get('road', '') or addr.get('pedestrian', '') or addr.get('footway', '') or addr.get('path', '')
        city = addr.get('city', '') or addr.get('town', '') or addr.get('village', '') or addr.get('hamlet', '') or addr.get('suburb', '')
        county = addr.get('county', '') or addr.get('state', '')
        country = addr.get('country', '')
    road = road or ''
    city = city or ''
    county = county or ''
    country = country or ''

    if road:
        row[H['road']] = road
    if city and not row[H['city']]:
        row[H['city']] = city
    if county and not row[H['region']]:
        row[H['region']] = county
    if country and not row[H['country']]:
        row[H['country']] = country
    if road or city or country:
        row[H['location_precision']] = 'precise'
    updated += 1

print(f'Updated {updated} argus rows from Nominatim cache')

# Write back
with open(CSV, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(header)
    for r in rows:
        writer.writerow(r)
print('Saved')
