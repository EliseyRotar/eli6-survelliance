"""Deep analysis: how many TV catalog cams are missing from CSV?"""
import json
import csv
import sys
import re

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

    # Build catalog IDs set
    catalog_ids = set()
    catalog_urls = set()
    for c in cams:
        src = c.get('source', '') or 'tv'
        cid = c.get('id', '')
        if src and cid:
            catalog_ids.add(f'{src}::{cid}')
        # Also add URL
        for u in [c.get('videoUrl'), c.get('imageUrl'), c.get('playerUrl'),
                  c.get('sourceUrl'), c.get('go2rtcWsUrl')]:
            if u:
                catalog_urls.add(u)
        for a in c.get('angles') or []:
            if isinstance(a, dict):
                for u in [a.get('videoUrl'), a.get('imageUrl'), a.get('sourceUrl')]:
                    if u:
                        catalog_urls.add(u)
    print(f'  {len(catalog_ids):,} unique source:id pairs', flush=True)
    print(f'  {len(catalog_urls):,} unique URLs from catalog', flush=True)

    # Load CSV
    print('[CSV] Loading...', flush=True)
    csv_ids = set()
    csv_urls = set()
    csv_urls_lower = set()
    csv_rows = 0
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        for row in csv.DictReader(f):
            csv_rows += 1
            # Check notes for trafficvision_id
            notes = row.get('notes', '') or ''
            for m in re.finditer(r'trafficvision_id=([^\s;,]+)', notes):
                csv_ids.add(m.group(1))
            # Check URL
            url = row.get('url', '') or ''
            lsurl = row.get('live_stream_url', '') or ''
            csv_urls.add(url)
            csv_urls.add(lsurl)
            if url:
                csv_urls_lower.add(url.lower())
            if lsurl:
                csv_urls_lower.add(lsurl.lower())
    print(f'  {csv_rows:,} rows', flush=True)
    print(f'  {len(csv_ids):,} trafficvision_id in notes', flush=True)
    print(f'  {len(csv_urls):,} URLs', flush=True)

    # Compute matches
    matched_ids = catalog_ids & csv_ids
    matched_urls = catalog_urls & csv_urls
    matched_urls_lower = {u.lower() for u in catalog_urls} & csv_urls_lower

    print(f'\n[MATCH]')
    print(f'  By ID: {len(matched_ids):,}', flush=True)
    print(f'  By URL (exact): {len(matched_urls):,}', flush=True)
    print(f'  By URL (lowercase): {len(matched_urls_lower):,}', flush=True)

    missing_ids = catalog_ids - csv_ids
    print(f'\n[MISSING]')
    print(f'  By ID: {len(missing_ids):,}', flush=True)

    # Show samples
    print('\nSample missing IDs:')
    for mid in list(missing_ids)[:10]:
        # Find the cam
        for c in cams:
            if f'{c.get("source","tv")}::{c.get("id","")}' == mid:
                vu = (c.get('videoUrl') or '')[:50]
                iu = (c.get('imageUrl') or '')[:50]
                print(f'  {mid}: V={vu} I={iu}')
                break

    # Save missing
    missing_list = []
    for c in cams:
        mid = f'{c.get("source","tv")}::{c.get("id","")}'
        if mid in missing_ids:
            missing_list.append(c)
    with open('tv_missing.json', 'w') as f:
        json.dump(missing_list, f)
    print(f'\nSaved {len(missing_list):,} missing cams to tv_missing.json', flush=True)


if __name__ == '__main__':
    main()
