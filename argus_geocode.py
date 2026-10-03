"""
PHASE 4C: Nominatim reverse geocoding for argus cams (rate-limited 1/sec).

Strategy: only process argus cams with non-default lat/lng and location_precision != 'host_default'
or 'no_coords'. Skip if already has road or via info.
"""
import csv
import re
import time
import urllib.request
import json
import ssl
from pathlib import Path

CSV_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

print("Reading CSV...")
with open(CSV_PATH, encoding='utf-8', newline='') as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = list(reader)
H = {k: i for i, k in enumerate(header)}
print(f"Total rows: {len(rows)}")

# Find argus cams that need geocoding (have real lat/lng, no road info yet)
TARGETS = []
seen_coords = set()  # dedupe (multiple cams at same exact lat/lng)
for ri, row in enumerate(rows):
    if len(row) != len(header):
        continue
    precision = row[H['location_precision']] if len(row) > H['location_precision'] else ''
    if precision not in ('approximate_from_region', 'no_coords', 'host_default'):
        continue
    if 'argus_cleanup_v1' not in (row[H['notes']] or ''):
        continue
    try:
        lat = float(row[H['lat']])
        lon = float(row[H['lon']])
    except:
        continue
    if abs(lat) < 0.0001 and abs(lon) < 0.0001:
        continue
    # Skip defaults
    if (lat, lon) in [(36.57, -118.09), (40.5023, -0.1908), (43.793, 142.28), (22.248, 114.15), (47.428, 11.695), (50.383, 11.885)]:
        continue
    # Dedupe: round to 4 decimal places
    key = (round(lat, 4), round(lon, 4))
    if key in seen_coords:
        continue
    seen_coords.add(key)
    TARGETS.append((ri, lat, lon))

print(f"Unique coords to geocode: {len(TARGETS)}")
print(f"Estimated time: {len(TARGETS)} seconds ({len(TARGETS)//3600} hours)")

# Try to load cached geocoding results
CACHE = Path(r'C:\Users\eli6-admin\AppData\Local\Temp\opencode\nominatim_cache.json')
CACHE.parent.mkdir(parents=True, exist_ok=True)
if CACHE.exists():
    with open(CACHE, encoding='utf-8') as f:
        cache = json.load(f)
    print(f"Loaded {len(cache)} cached geocoding results")
else:
    cache = {}

# Process in chunks, saving every 1000
processed = 0
for ri, lat, lon in TARGETS:
    key = f"{lat:.6f},{lon:.6f}"
    if key in cache:
        addr = cache[key]
    else:
        # Call Nominatim
        try:
            url = f'https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&zoom=16&addressdetails=1'
            req = urllib.request.Request(url, headers={'User-Agent': 'eli6-surveillance/1.0'})
            with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
                data = json.loads(r.read())
            addr = data.get('address', {})
            cache[key] = addr
        except Exception as e:
            cache[key] = None
        time.sleep(1.1)  # rate limit
    processed += 1

    # Save cache every 200
    if processed % 200 == 0:
        with open(CACHE, 'w', encoding='utf-8') as f:
            json.dump(cache, f)
        print(f'  {processed}/{len(TARGETS)} done', flush=True)

    # Update the row in memory
    row = rows[ri]
    if addr:
        # Extract road, city, etc.
        road = addr.get('road', '') or addr.get('pedestrian', '') or addr.get('footway', '') or addr.get('path', '')
        city = addr.get('city', '') or addr.get('town', '') or addr.get('village', '') or addr.get('hamlet', '') or addr.get('suburb', '')
        county = addr.get('county', '')
        state = addr.get('state', '')
        country = addr.get('country', '')
        # Add to address if not already
        existing_addr = row[H['address']] or ''
        addr_parts = [p for p in (road, city, state, country) if p]
        if addr_parts and addr_parts[0] not in existing_addr:
            row[H['address']] = ' | '.join(addr_parts)[:300]
        if road:
            row[H['road']] = road[:100]
        # Update city if missing
        if not row[H['city']] and city:
            row[H['city']] = city[:100]
        # Update precision
        row[H['location_precision']] = 'precise'
    else:
        row[H['location_precision']] = 'no_geocode_result'

# Save final cache
with open(CACHE, 'w', encoding='utf-8') as f:
    json.dump(cache, f)

print(f'Processed {processed} cams. Writing CSV...')

# Write back
with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
print("Done.")
