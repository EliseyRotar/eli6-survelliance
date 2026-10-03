"""Ingest OpenCCTV new cams into DB.
We have 1,493 new cams from sources not in our DB.
Map to controllable_Webcams.csv schema."""
import json, csv, sys
from pathlib import Path
import re
sys.stdout = open(sys.stdout.fileno(), 'w', encoding='utf-8')

src = Path(r'C:\Users\eli6-admin\AppData\Local\Temp\oc_new_cams.json')
csv_path = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')

with src.open(encoding='utf-8') as f:
    oc_new = json.load(f)
print(f'OpenCCTV new cams: {len(oc_new)}')

# Filter out cams that don't look like cameras (test/sample cams)
def is_valid(cam):
    name = cam.get('name','')
    if 'test' in name.lower() or 'sample' in name.lower():
        return False
    feed = cam.get('feed_url','')
    if not feed:
        return False
    return True

valid = [c for c in oc_new if is_valid(c)]
print(f'Valid: {len(valid)}')

# Read existing CSV
with csv_path.open(encoding='utf-8', newline='') as f:
    rdr = csv.DictReader(f)
    fieldnames = rdr.fieldnames
    rows = list(rdr)
print(f'Existing rows: {len(rows)}')

# Existing slugs/idx
existing_urls = set(r.get('live_stream_url','') for r in rows)
existing_idxs = set(int(r['idx']) for r in rows if r.get('idx','').isdigit())
max_idx = max(existing_idxs)

new_rows = []
skipped = 0
for cam in valid:
    url = cam.get('feed_url','')
    if url in existing_urls:
        skipped += 1
        continue

    name = cam.get('name','') or ''
    city = cam.get('city','') or ''
    state = cam.get('state','') or ''
    country = cam.get('country','') or ''
    if country == 'US': country = 'United States'

    source = cam.get('source','') or ''
    feed_type = cam.get('feed_type','') or ''
    category = cam.get('category','') or ''
    direction = cam.get('direction','') or ''
    description = cam.get('description','') or ''
    lat = cam.get('lat')
    lon = cam.get('lng')
    if lat is None or lon is None:
        lat = lon = ''

    # Project name
    proj_name_parts = []
    if name: proj_name_parts.append(name)
    if state: proj_name_parts.append(state)
    if country: proj_name_parts.append(country)
    proj_name_parts.append(f'#{source}')
    if cam.get('id'): proj_name_parts.append(f'#{cam["id"]}')
    proj_name = ' · '.join(proj_name_parts)

    # Road
    road = f'OpenCCTV · {source}' if source else 'OpenCCTV'

    idx = str(max_idx + 1 + len(new_rows))
    # type
    if feed_type == 'm3u8': ctype = 'hls'
    elif feed_type == 'image': ctype = 'mjpeg'
    elif feed_type == 'iframe': ctype = 'iframe'
    else: ctype = feed_type or 'unknown'

    row = {
        'idx': idx,
        'live_stream_url': url,
        'project_name': proj_name[:200],
        'city': city,
        'region': state,
        'country': country,
        'lat': str(lat) if lat != '' else '',
        'lon': str(lon) if lon != '' else '',
        'road': road,
        'location_precision': 'exact' if lat else 'region',
        'live_status': 'live',
        'enabled': '1',
        'host': re.sub(r'https?://([^/]+).*', r'\1', url),
        'type': ctype,
        'category': category,
        'isp': source,
        'description': description[:300] if description else '',
        'geo_source': 'OpenCCTV API',
        'notes': f'OpenCCTV ID: {cam.get("id","")}',
    }

    for fn in fieldnames:
        if fn not in row:
            row[fn] = ''
    new_rows.append(row)

print(f'\nNew rows: {len(new_rows)} Skipped (dup): {skipped}')

# Backup
import shutil, datetime
backup_name = f'backup_20260915_{datetime.datetime.now().strftime("%H%M%S")}_session38b'
backup_path = csv_path.parent / 'backups' / backup_name
backup_path.mkdir(parents=True, exist_ok=True)
shutil.copy2(csv_path, backup_path / csv_path.name)
print(f'Backed up to {backup_path}')

# Write
all_rows = rows + new_rows
with csv_path.open('w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    for r in all_rows:
        w.writerow(r)
print(f'Wrote {len(all_rows)} rows (was {len(rows)})')

# Save scripts
shutil.copy2(Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\ingest_oc_new.py'),
             backup_path / 'ingest_oc_new.py')
