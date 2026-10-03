"""Insecam scrape by country code - try many country-specific subdomains.

Insecam organizes cams by country, not just brand. URLs are:
- https://www.insecam.org/en/bycountry/<CC>/?page=N
- https://www.insecam.org/en/bytype/<brand>/?page=N
- https://www.insecam.org/en/cams/ (all cams paginated)
- https://www.insecam.org/en/bytag/<tag>/?page=N
"""
import csv
import os
import time
import json
import re
import urllib.request
import ssl
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

import glob

CSV_PATH = None
for f in glob.glob(r'C:\Users\eli6-admin\Documents\**/controllable_Webcams.csv', recursive=True):
    CSV_PATH = f
    break
if not CSV_PATH:
    print('CSV not found')
    exit(1)
print(f'CSV: {CSV_PATH}')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def fetch(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, r.headers.get('Content-Type', ''), r.read()
    except urllib.error.HTTPError as e:
        return e.code, '', b''
    except Exception as e:
        return -1, str(e)[:100], b''


# All insecam country codes (all 2-letter ISO codes)
COUNTRY_CODES = [
    'US', 'JP', 'DE', 'IT', 'KR', 'FR', 'GB', 'CA', 'ES', 'MX', 'BR', 'RU',
    'IN', 'CN', 'TW', 'TH', 'VN', 'ID', 'MY', 'PH', 'AU', 'NZ', 'NL', 'BE',
    'PL', 'CZ', 'HU', 'AT', 'CH', 'SE', 'NO', 'FI', 'DK', 'IE', 'PT', 'GR',
    'TR', 'IL', 'AE', 'SA', 'EG', 'ZA', 'NG', 'KE', 'AR', 'CL', 'CO', 'PE',
    'VE', 'EC', 'BO', 'CR', 'PA', 'GT', 'HN', 'NI', 'SV', 'CU', 'DO', 'PR',
    'JM', 'HT', 'TT', 'PA', 'PK', 'BD', 'LK', 'NP', 'MM', 'KH', 'LA', 'SG',
    'HK', 'MO', 'IR', 'IQ', 'SY', 'LB', 'JO', 'YE', 'OM', 'QA', 'KW', 'BH',
    'AF', 'UZ', 'KZ', 'KG', 'TJ', 'TM', 'AZ', 'AM', 'GE', 'BY', 'UA', 'MD',
    'LV', 'LT', 'EE', 'IS', 'LU', 'MT', 'CY', 'BG', 'RO', 'RS', 'HR', 'SI',
    'BA', 'MK', 'AL', 'ME', 'XK', 'DZ', 'MA', 'TN', 'LY', 'SD', 'ET', 'TZ',
    'UG', 'ZW', 'ZM', 'MW', 'MZ', 'AO', 'CD', 'CG', 'GA', 'CM', 'CI', 'GH',
    'SN', 'ML', 'BF', 'NE', 'TD', 'SO', 'RW', 'BI', 'DJ', 'ER', 'SS', 'CF',
    'FJ', 'PG', 'WS', 'TO', 'VU', 'SB', 'KI', 'FM', 'PW', 'MH', 'NR', 'TV',
    'MN', 'KP', 'BT', 'MV',
]


def scrape_country(cc, page):
    """Scrape one page of insecam cams for a country."""
    url = f'https://www.insecam.org/en/bycountry/{cc}/?page={page}'
    status, ct, body = fetch(url, timeout=12)
    if status != 200:
        return []
    try:
        html = body.decode('utf-8', errors='replace')
    except:
        return []
    cams = []
    # Find all cam URLs - insecam.org shows cams in <a href="/en/view/...">
    for m in re.finditer(r'href="(/en/view/(\d+)/?)"', html):
        cam_id = m.group(2)
        cams.append({
            'id': cam_id,
            'url': f'https://www.insecam.org/en/view/{cam_id}/',
            'country': cc,
            'page': page,
        })
    # Also look for direct image/stream URLs in iframe
    for m in re.finditer(r'(?:src|data-src)="(https?://[^"]+)"', html):
        u = m.group(1)
        if re.search(r'\.m3u8|mjpg|video|stream|axis-cgi|onvif|h264|hls', u, re.I):
            cams.append({
                'id': 'inline',
                'url': u,
                'country': cc,
                'page': page,
            })
    return cams


def main():
    # Load existing
    existing = set()
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            if row.get('url'):
                existing.add(row['url'])
    print(f'  CSV has {len(existing):,} URLs')

    # Check insecam home page first
    status, ct, body = fetch('https://www.insecam.org/en/bycountry/', timeout=12)
    print(f'  insecam bycountry root: {status} {ct[:30]}')
    if status == 200:
        # Extract country list
        try:
            html = body.decode('utf-8', errors='replace')
            ccs = re.findall(r'/en/bycountry/([A-Z]{2})/', html)
            ccs = list(set(ccs))
            print(f'  Available countries: {len(ccs)}')
            for cc in sorted(ccs)[:20]:
                print(f'    {cc}')
        except Exception as e:
            print(f'  err: {e}')

    # Try random countries
    total_new = 0
    out_file = 'insecam_country_results.jsonl'
    with open(out_file, 'w', encoding='utf-8') as f_out:
        # Test first page of each country
        for cc in random.sample(COUNTRY_CODES, min(20, len(COUNTRY_CODES))):
            for page in range(1, 4):
                cams = scrape_country(cc, page)
                for c in cams:
                    f_out.write(json.dumps(c) + '\n')
                if cams:
                    print(f'  {cc} p{page}: {len(cams)} cams')
                if not cams and page > 1:
                    break
                total_new += len(cams)
                time.sleep(0.3)
            time.sleep(0.5)
    print(f'\n[TOTAL] {total_new} cams found')


if __name__ == '__main__':
    main()
