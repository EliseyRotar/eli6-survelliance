"""
OpenCCTV extra fetch - more pages of high-yield countries.
"""
import requests
import json
import time
from pathlib import Path

OUT = Path(r'C:\Users\eli6-admin\AppData\Local\Temp\opencode\opencctv_extra_v2.json')

COUNTRIES = [
    'TR', 'KR', 'ID', 'TH', 'IL', 'RU', 'AR', 'NL', 'PT', 'GR',
    'RO', 'IE', 'NZ', 'ES', 'IT', 'DE', 'JP', 'GB', 'FR', 'CA',
    'BG', 'HR', 'HU', 'PL', 'CZ', 'AT', 'CH', 'BE', 'DK', 'SE',
    'NO', 'FI', 'EE', 'LV', 'LT', 'SK', 'SI', 'RS', 'UA', 'BY',
    'AE', 'SA', 'EG', 'MA', 'NG', 'KE', 'ZA', 'CL', 'CO', 'PE',
    'MX', 'BR', 'IN', 'CN', 'TW', 'HK', 'MY', 'SG', 'PH', 'VN',
    'AU', 'PG', 'FJ', 'IS', 'KZ', 'KG', 'UZ',
]

BASE = 'https://www.opencctv.org/api/cameras/list'
PAGE_SIZE = 100
PAGES_PER_COUNTRY = 20  # up to 2000 cams per country

all_cams = {}
total_added = 0
errors = 0

# Load existing
EXISTING = Path(r'C:\Users\eli6-admin\AppData\Local\Temp\opencode\opencctv_us_all.json')
if EXISTING.exists():
    try:
        with open(EXISTING, encoding='utf-8') as f:
            for c in json.load(f):
                all_cams[c.get('feed_url', c.get('image_url', ''))] = c
    except Exception as e:
        print(f'  Skip existing: {e}')

for path in [
    r'C:\Users\eli6-admin\AppData\Local\Temp\opencode\opencctv_intl.json',
    r'C:\Users\eli6-admin\AppData\Local\Temp\opencode\opencctv_eu.json',
    r'C:\Users\eli6-admin\AppData\Local\Temp\opencode\opencctv_eu_v2.json',
    r'C:\Users\eli6-admin\AppData\Local\Temp\opencode\opencctv_world.json',
    r'C:\Users\eli6-admin\AppData\Local\Temp\opencode\opencctv_asia_africa.json',
    r'C:\Users\eli6-admin\AppData\Local\Temp\opencode\opencctv_global.json',
]:
    if Path(path).exists():
        try:
            with open(path, encoding='utf-8') as f:
                for c in json.load(f):
                    key = c.get('feed_url', c.get('image_url', ''))
                    if key and key not in all_cams:
                        all_cams[key] = c
        except Exception as e:
            print(f'  Skip {path}: {e}')

print(f'Starting with {len(all_cams)} cams already cached')

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 ELI6-surveillance/1.0'})

for cc in COUNTRIES:
    for page in range(1, PAGES_PER_COUNTRY + 1):
        url = f'{BASE}?country={cc}&page={page}&limit={PAGE_SIZE}&sort=-view_count'
        try:
            r = session.get(url, timeout=20)
            if r.status_code != 200:
                if page == 1:
                    print(f'  {cc}: page 1 status {r.status_code}')
                errors += 1
                if errors > 10:
                    print('Too many errors, stopping')
                    break
                continue
            data = r.json()
            cams = data.get('data', data.get('cameras', data.get('items', [])))
            if isinstance(data, list):
                cams = data
            if not cams:
                break
            for c in cams:
                if not isinstance(c, dict):
                    continue
                key = c.get('feed_url', c.get('image_url', ''))
                if not key:
                    continue
                if key not in all_cams:
                    all_cams[key] = c
                    total_added += 1
            if len(cams) < PAGE_SIZE:
                break
        except Exception as e:
            errors += 1
            if errors > 10:
                break
            time.sleep(1)

print(f'Total cams now: {len(all_cams)} (added {total_added})')
with open(OUT, 'w') as f:
    json.dump(list(all_cams.values()), f)
print(f'Saved to {OUT}')
