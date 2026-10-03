"""Final check - how many TV cams are in CSV vs catalog, with proper ID parsing."""
import json
import csv
import re
import sys

sys.stdout.reconfigure(line_buffering=True)

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
TV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_catalog_full.json'


def main():
    csv.field_size_limit(2**31 - 1)

    # Load catalog
    print('[TV] Loading catalog...', flush=True)
    with open(TV_PATH) as f:
        catalog = json.load(f)
    cams = catalog['cameras']
    print(f'  {len(cams):,} cams in catalog', flush=True)

    # Build catalog IDs set (using both : and :: as separators)
    catalog_ids = set()
    catalog_urls = set()
    for c in cams:
        src = c.get('source', '') or 'tv'
        cid = c.get('id', '')
        if src and cid:
            catalog_ids.add(f'{src}:{cid}')  # single colon
            catalog_ids.add(f'{src}::{cid}')  # double colon
        for u in [c.get('videoUrl'), c.get('imageUrl'), c.get('playerUrl'),
                  c.get('sourceUrl'), c.get('go2rtcWsUrl')]:
            if u:
                catalog_urls.add(u.lower())
    print(f'  {len(catalog_ids):,} unique IDs (with both : and ::)', flush=True)
    print(f'  {len(catalog_urls):,} unique URLs', flush=True)

    # Load CSV
    print('[CSV] Loading...', flush=True)
    csv_ids = set()
    csv_urls = set()
    csv_rows = 0
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        for row in csv.DictReader(f):
            csv_rows += 1
            notes = row.get('notes', '') or ''
            for m in re.finditer(r'trafficvision_id=([^\s;,]+)', notes):
                csv_ids.add(m.group(1))
            url = (row.get('url', '') or '').lower()
            lsurl = (row.get('live_stream_url', '') or '').lower()
            if url:
                csv_urls.add(url)
            if lsurl:
                csv_urls.add(lsurl)
    print(f'  {csv_rows:,} rows', flush=True)
    print(f'  {len(csv_ids):,} trafficvision_id in notes', flush=True)
    print(f'  {len(csv_urls):,} URLs', flush=True)

    # Compute matches
    matched_ids = catalog_ids & csv_ids
    matched_urls = catalog_urls & csv_urls

    print(f'\n[MATCH]')
    print(f'  By ID: {len(matched_ids):,}', flush=True)
    print(f'  By URL: {len(matched_urls):,}', flush=True)

    # Combined - cams matched by EITHER ID or URL
    matched = set()
    for c in cams:
        src = c.get('source', '') or 'tv'
        cid = c.get('id', '')
        ids_to_check = {f'{src}:{cid}', f'{src}::{cid}'}
        if ids_to_check & csv_ids:
            matched.add(f'{src}:{cid}')
            continue
        urls = [c.get('videoUrl'), c.get('imageUrl'), c.get('playerUrl'),
                c.get('sourceUrl'), c.get('go2rtcWsUrl')]
        if any((u or '').lower() in csv_urls for u in urls):
            matched.add(f'{src}:{cid}')

    print(f'\n[UNIQUE MATCH]')
    print(f'  Catalog cams in CSV: {len(matched):,}', flush=True)
    print(f'  Catalog cams missing: {len(cams) - len(matched):,}', flush=True)

    # Save missing list
    missing = []
    for c in cams:
        src = c.get('source', '') or 'tv'
        cid = c.get('id', '')
        if f'{src}:{cid}' not in matched:
            missing.append(c)
    with open('tv_missing.json', 'w') as f:
        json.dump(missing, f)
    print(f'  Saved {len(missing):,} missing to tv_missing.json', flush=True)

    # Group missing by source
    from collections import Counter
    src_counts = Counter(c.get('source', 'unknown') for c in missing)
    print(f'\n  Missing by source (top 20):')
    for s, c in src_counts.most_common(20):
        print(f'    {s}: {c}')


if __name__ == '__main__':
    main()
