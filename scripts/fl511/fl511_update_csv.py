"""Match fl511 live URLs to existing CSV rows by imageId and update CSV."""
import csv
import os
import json
import time
import re
import random
from collections import Counter

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LIVE_DATA = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\fl511_live_urls.json'


def main():
    csv.field_size_limit(2**31 - 1)

    # Load live URLs
    with open(LIVE_DATA, encoding='utf-8') as f:
        live = json.load(f)
    print(f'Loaded {len(live):,} live URLs', flush=True)

    # Build map: fl511 image_id (which is the cam_id in our data) -> live URL
    # Wait, in fl511, cam_id == image_id == id (all 614, 615, etc.)
    live_by_id = {}
    for l in live:
        cid = str(l['fl511_cam_id'])
        if l.get('live_url'):
            live_by_id[cid] = l['live_url']

    # Load CSV
    print(f'Loading CSV...', flush=True)
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        header = reader.fieldnames
    print(f'  {len(rows):,} rows', flush=True)

    # The existing fl511 entries have notes like "argus_id=opencctv_state511_s511-FL-1219"
    # Where 1219 is NOT the fl511 imageId. The actual argus_id matches the imageId
    # Let's check by looking at one entry
    fl511_rows = []
    for i, row in enumerate(rows):
        if (row.get('host', '') or '').lower() == 'fl511.com':
            fl511_rows.append((i, row))

    print(f'  {len(fl511_rows):,} fl511 rows', flush=True)

    # Show sample
    if fl511_rows:
        i, row = fl511_rows[0]
        notes = row.get('notes', '') or ''
        print(f'  Sample notes: {notes[:300]}', flush=True)

    # We need to figure out the matching key. Let me check a known cam
    # Cam 614 in fl511 = I-4 @ MM 60.6 EB
    # Cam 615 in fl511 = I-95 @ MM 183.3 SB
    # These are likely the "FL-NNNN" values in argus_id

    # But the argus_id might be an internal ID, not the fl511 imageId
    # Let me try matching by location string

    # The fl511 data has location, roadway, county
    # The CSV rows have description, city, etc
    # Let me try matching by location

    # Build location-based index for fl511
    fl511_by_location = {}
    for l in live:
        loc = l.get('location', '').strip()
        if loc:
            fl511_by_location[loc] = l

    # Also build by description (imageId is in imageUrl, e.g., /map/Cctv/614)
    # But we don't have imageId in CSV

    # Try matching by location
    matched = 0
    for i, row in fl511_rows:
        # Try matching by description
        desc = (row.get('description', '') or '').strip()
        title = (row.get('page_title', '') or '').strip()
        city = (row.get('city', '') or '').strip()
        notes = row.get('notes', '') or ''

        # Build candidates
        candidates = [desc, title, notes]

        for cand in candidates:
            cand = cand.strip()
            if cand and cand in fl511_by_location:
                live_url = fl511_by_location[cand]['live_url']
                # Update this row
                rows[i]['live_stream_url'] = live_url
                rows[i]['url'] = live_url
                rows[i]['type'] = 'video-hls'
                rows[i]['notes'] = (rows[i].get('notes', '') or '') + f' | fl511_live_url'
                matched += 1
                break

    print(f'\nMatched {matched} of {len(fl511_rows)} fl511 rows by location', flush=True)

    # Save CSV with retries
    tmp = CSV_PATH + '.tmp'
    for attempt in range(20):
        try:
            with open(tmp, 'w', encoding='utf-8', newline='') as f:
                w = csv.DictWriter(f, fieldnames=header, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
                w.writeheader()
                w.writerows(rows)
            os.replace(tmp, CSV_PATH)
            print(f'Saved CSV with {matched} updated fl511 rows', flush=True)
            return
        except PermissionError:
            time.sleep(2 + random.uniform(0, 3))
    print('ERROR: Could not save CSV', flush=True)


if __name__ == '__main__':
    main()
