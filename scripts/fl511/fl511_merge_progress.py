"""Merge progress from all FL511 token sources into the main file.

Sources:
- fl511_divas_full_tokens.json (the main file)
- fl511_divas_direct.json (direct API worker)
- fl511_divas_browser.json (browser worker)

Priority: prefer the record with a real divas_token. Merge carefully to preserve all.
"""
import json
import os
import csv
import re
import time
import random
import urllib.request
import ssl
from collections import Counter

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
MAIN = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\fl511_divas_full_tokens.json'
DIRECT = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\fl511_divas_direct.json'
BROWSER = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\fl511_divas_browser.json'

def main():
    # Load all sources
    sources = {}
    for name, p in [('main', MAIN), ('direct', DIRECT), ('browser', BROWSER)]:
        if os.path.exists(p):
            with open(p) as f:
                sources[name] = json.load(f)
            print(f'  {name}: {len(sources[name]):,}', flush=True)

    # Merge: prefer records with divas_token
    merged = {}
    for name, data in sources.items():
        for cam_id, rec in data.items():
            if not isinstance(rec, dict):
                continue
            if cam_id not in merged:
                merged[cam_id] = rec
                continue
            # Prefer the one with a real divas_token
            if rec.get('divas_token') and not merged[cam_id].get('divas_token'):
                merged[cam_id] = rec
            elif not rec.get('no_token') and merged[cam_id].get('no_token'):
                merged[cam_id] = rec
            # Otherwise keep the first (no improvement)

    n_with = sum(1 for v in merged.values() if v.get('divas_token'))
    n_total = sum(1 for v in merged.values() if not v.get('no_token'))
    n_template = sum(1 for v in merged.values() if v.get('no_token'))
    print(f'\nMerged: {len(merged):,} total', flush=True)
    print(f'  with divas token: {n_with:,}', flush=True)
    print(f'  with template only: {n_template:,}', flush=True)

    # Save merged result
    tmp = MAIN + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(merged, f, indent=2)
    try:
        os.replace(tmp, MAIN)
        print(f'  Saved merged to {MAIN}', flush=True)
    except OSError as e:
        print(f'  Save err: {e}', flush=True)


if __name__ == '__main__':
    main()
