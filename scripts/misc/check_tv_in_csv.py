"""Check how many TV cams are in the master CSV vs the catalog.

Builds a set of (lat, lng, country_code, source) tuples from both,
and reports overlap.
"""
import csv
import json
import sys
import re

sys.stdout.reconfigure(line_buffering=True)

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
TV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_catalog_full.json'


def main():
    csv.field_size_limit(2**31 - 1)
    # Load TV catalog
    print('[TV] Loading catalog...', flush=True)
    with open(TV_PATH, 'r') as f:
        catalog = json.load(f)
    cams = catalog['cameras']
    print(f'  {len(cams):,} cams in catalog', flush=True)

    # Build set of TV source + ID pairs
    tv_ids = set()
    for c in cams:
        src = c.get('source', '')
        cid = c.get('id', '')
        if src and cid:
            tv_ids.add(f'{src}::{cid}')
    print(f'  {len(tv_ids):,} unique source:id pairs', flush=True)

    # Load CSV
    print('[CSV] Loading...', flush=True)
    csv_tv = 0
    csv_other = 0
    for row in csv.DictReader(open(CSV_PATH, 'r', encoding='utf-8', errors='replace')):
        pn = row.get('project_name', '') or ''
        if 'trafficvision' in pn.lower() or pn == 'trafficvision_full':
            csv_tv += 1
        else:
            csv_other += 1
    print(f'  Trafficvision rows: {csv_tv:,}', flush=True)
    print(f'  Other rows: {csv_other:,}', flush=True)
    print(f'  Catalog has: {len(cams):,}', flush=True)
    print(f'  Missing: {len(cams) - csv_tv:,}', flush=True)


if __name__ == '__main__':
    main()
