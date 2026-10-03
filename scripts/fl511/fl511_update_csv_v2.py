"""Update CSV with fl511 template URLs (no auth token). 4265 cams get direct templates.

We can also try to get tokens for those cams later. For now, use template URLs.
"""
import csv
import os
import json
import time
import re
import random
from collections import Counter

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
FL511_DATA = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\fl511_cams_with_live.json'


def main():
    # Load fl511 cams
    with open(FL511_DATA, encoding='utf-8') as f:
        cams = json.load(f)
    print(f'Loaded {len(cams):,} fl511 cams')

    # Build map: location -> template URL
    live_by_location = {}
    for c in cams:
        loc = c.get('location', '').strip()
        if not loc:
            continue
        template = c.get('video_url_template', '')
        if template:
            live_by_location[loc] = template

    print(f'  {len(live_by_location):,} locations with templates')

    csv.field_size_limit(2**31 - 1)
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        header = reader.fieldnames

    # Find fl511 rows
    fl511_rows = [(i, r) for i, r in enumerate(rows) if (r.get('host', '') or '').lower() == 'fl511.com']
    print(f'  {len(fl511_rows):,} fl511 rows in CSV')

    n_updated = 0
    n_no_match = 0
    unmatched = []
    for i, row in fl511_rows:
        desc = (row.get('description', '') or '').strip()
        title = (row.get('page_title', '') or '').strip()
        notes = row.get('notes', '') or ''

        match = None
        for key in (desc, title):
            if key and key in live_by_location:
                match = live_by_location[key]
                break
        if not match:
            for loc, url in live_by_location.items():
                if loc and (loc in desc or loc in title):
                    match = url
                    break
        if not match and notes:
            # Try to find by roadway + direction
            roadway = ''
            m = re.search(r'roadway=([^;]+)', notes)
            if m:
                roadway = m.group(1).strip()
            direction = ''
            m = re.search(r'dir=([^;]+)', notes)
            if m:
                direction = m.group(1).strip()
            if roadway:
                for loc, url in live_by_location.items():
                    if roadway in loc:
                        match = url
                        break

        if match:
            rows[i]['live_stream_url'] = match
            rows[i]['url'] = match
            rows[i]['type'] = 'video-hls'
            existing_notes = rows[i].get('notes', '') or ''
            if 'fl511_live' not in existing_notes:
                rows[i]['notes'] = existing_notes + ' | fl511_live_template'
            n_updated += 1
        else:
            n_no_match += 1
            if len(unmatched) < 10:
                unmatched.append((i, desc[:60], title[:60]))

    print(f'\n  Updated {n_updated} of {len(fl511_rows)} rows')
    print(f'  {n_no_match} did not match')
    if unmatched:
        print(f'  Sample unmatched:')
        for i, d, t in unmatched:
            print(f'    [{i}] desc="{d}" title="{t}"')

    # Save
    tmp = CSV_PATH + '.tmp'
    for attempt in range(20):
        try:
            with open(tmp, 'w', encoding='utf-8', newline='') as f:
                w = csv.DictWriter(f, fieldnames=header, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
                w.writeheader()
                w.writerows(rows)
            os.replace(tmp, CSV_PATH)
            print(f'\n  Saved CSV with {n_updated} fl511 rows updated')
            return
        except PermissionError:
            time.sleep(2 + random.uniform(0, 3))
    print('ERROR: Could not save CSV')


if __name__ == '__main__':
    main()
