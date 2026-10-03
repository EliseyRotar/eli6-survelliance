"""Re-add fl511 cams to CSV that were removed by reap (but have fresh tokens)."""
import csv
import json
import os
import time
import random

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
TOKENS_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\fl511_divas_full_tokens.json'
CAMS_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\fl511_cams_with_live.json'

print('Loading fl511 cams...', flush=True)
with open(CAMS_PATH) as f:
    fl511_cams = json.load(f)
fl511_cams = [c for c in fl511_cams if c.get('video_url_template') and c.get('image_id')]
print(f'  {len(fl511_cams):,} fl511 cams with templates', flush=True)

# Load tokens
print('Loading tokens...', flush=True)
with open(TOKENS_PATH) as f:
    tokens = json.load(f)

# Build location -> url map
url_by_location = {}
for c in fl511_cams:
    cid = str(c['cam_id'])
    loc = c.get('location', '').strip()
    if not loc:
        continue
    if cid in tokens:
        info = tokens[cid]
        if info.get('live_url'):
            url_by_location[loc] = info['live_url']

print(f'  {len(url_by_location):,} locations with live URLs', flush=True)

# Load CSV
print('Loading CSV...', flush=True)
csv.field_size_limit(2**31-1)
with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    header = reader.fieldnames
print(f'  {len(rows):,} rows', flush=True)

# Find max idx
max_idx = 0
for row in rows:
    try:
        idx = int(row.get('idx', 0))
        max_idx = max(max_idx, idx)
    except:
        pass

# Check which locations are missing
existing_urls = set()
for row in rows:
    u = (row.get('url') or '').lower()
    if 'divas' in u:
        existing_urls.add(u)

# Add new fl511 rows
n_added = 0
fl511_rows = []
for c in fl511_cams:
    loc = c.get('location', '').strip()
    if not loc:
        continue
    cid = str(c['cam_id'])
    if cid in tokens and tokens[cid].get('live_url'):
        live_url = tokens[cid]['live_url']
        # Check if URL already in CSV
        if live_url.lower() not in existing_urls:
            max_idx += 1
            n_added += 1
            new_row = {h: '' for h in header}
            new_row['idx'] = str(max_idx)
            new_row['csv_id'] = f'fl511_{max_idx:04d}'
            new_row['project_name'] = loc
            new_row['url'] = live_url.split('?')[0]  # URL without token
            new_row['live_stream_url'] = live_url
            new_row['type'] = 'video'
            new_row['enabled'] = 'True'
            new_row['live_status'] = 'live'
            new_row['http_status'] = '200'
            new_row['content_type'] = 'application/vnd.apple.mpegurl'
            new_row['description'] = '**cam view** IP camera (FL511 feed, requires token)'
            new_row['confidence'] = 'high'
            new_row['notes'] = 'fl511; systemSourceId={}; county={}'.format(
                c.get('system_source_id', ''),
                c.get('county', '')
            )
            fl511_rows.append(new_row)

print(f'\n  Adding {n_added:,} new fl511 rows', flush=True)

if n_added > 0:
    tmp = CSV_PATH + '.tmp'
    for attempt in range(20):
        try:
            with open(tmp, 'w', encoding='utf-8', newline='') as f:
                w = csv.DictWriter(f, fieldnames=header, lineterminator='\n', quoting=csv.QUOTE_MINIMAL, extrasaction='ignore')
                w.writeheader()
                chunk_size = 10000
                for i in range(0, len(rows), chunk_size):
                    w.writerows(rows[i:i+chunk_size])
                # Add fl511 rows
                for fr in fl511_rows:
                    w.writerow(fr)
            os.replace(tmp, CSV_PATH)
            print(f'  Saved CSV with {n_added:,} new fl511 rows', flush=True)
            print(f'  CSV now has {len(rows) + n_added:,} rows', flush=True)
            break
        except PermissionError as e:
            print(f'  retry {attempt}: {e}', flush=True)
            time.sleep(2 + random.uniform(0, 3))
