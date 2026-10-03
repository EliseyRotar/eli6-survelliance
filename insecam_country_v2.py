"""Parallel insecam country scrape - get all available countries.

Scrapes /en/bycountry/<CC>/?page=N for many countries in parallel.
Adds only cams with new URLs to CSV.
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
from collections import Counter

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


def fetch(url, timeout=10):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, r.headers.get('Content-Type', ''), r.read()
    except urllib.error.HTTPError as e:
        return e.code, '', b''
    except Exception as e:
        return -1, str(e)[:100], b''


# All insecam country codes (alphabetized)
ALL_CC = [
    'US', 'JP', 'DE', 'IT', 'KR', 'FR', 'GB', 'CA', 'ES', 'MX', 'BR', 'RU',
    'IN', 'CN', 'TW', 'TH', 'VN', 'ID', 'MY', 'PH', 'AU', 'NZ', 'NL', 'BE',
    'PL', 'CZ', 'HU', 'AT', 'CH', 'SE', 'NO', 'FI', 'DK', 'IE', 'PT', 'GR',
    'TR', 'IL', 'AE', 'SA', 'EG', 'ZA', 'NG', 'KE', 'AR', 'CL', 'CO', 'PE',
    'VE', 'EC', 'BO', 'CR', 'PA', 'GT', 'HN', 'NI', 'SV', 'CU', 'DO', 'PR',
    'JM', 'HT', 'TT', 'PK', 'BD', 'LK', 'NP', 'MM', 'KH', 'LA', 'SG',
    'HK', 'MO', 'IR', 'IQ', 'SY', 'LB', 'JO', 'YE', 'OM', 'QA', 'KW', 'BH',
    'AF', 'UZ', 'KZ', 'KG', 'TJ', 'TM', 'AZ', 'AM', 'GE', 'BY', 'UA', 'MD',
    'LV', 'LT', 'EE', 'IS', 'LU', 'MT', 'CY', 'BG', 'RO', 'RS', 'HR', 'SI',
    'BA', 'MK', 'AL', 'ME', 'DZ', 'MA', 'TN', 'LY', 'SD', 'ET', 'TZ',
    'UG', 'ZW', 'ZM', 'MW', 'MZ', 'AO', 'CG', 'GA', 'CM', 'CI', 'GH',
    'SN', 'ML', 'BF', 'NE', 'TD', 'SO', 'RW', 'BI', 'DJ', 'ER', 'SS', 'CF',
    'FJ', 'PG', 'WS', 'TO', 'VU', 'SB', 'KI', 'FM', 'PW', 'MH', 'NR', 'TV',
    'MN', 'BT', 'MV', 'CO', 'VE', 'EC',
]


def scrape_country(cc, max_pages=3):
    """Scrape all pages for a country."""
    out = []
    for page in range(1, max_pages + 1):
        url = f'https://www.insecam.org/en/bycountry/{cc}/?page={page}'
        status, ct, body = fetch(url, timeout=8)
        if status != 200:
            break
        try:
            html = body.decode('utf-8', errors='replace')
        except:
            break
        cams = []
        for m in re.finditer(r'href="(/en/view/(\d+)/?)"', html):
            cam_id = m.group(2)
            cams.append({
                'id': cam_id,
                'url': f'https://www.insecam.org/en/view/{cam_id}/',
                'country': cc,
            })
        out.extend(cams)
        if not cams:
            break
        time.sleep(0.2)
    return out


def get_direct_url(cam_id, timeout=8):
    """Visit insecam cam page and extract direct image/video URL."""
    url = f'https://www.insecam.org/en/view/{cam_id}/'
    status, ct, body = fetch(url, timeout=timeout)
    if status != 200:
        return None, None, None
    try:
        html = body.decode('utf-8', errors='replace')
    except:
        return None, None, None
    # Find image URL
    m = re.search(r'<img[^>]+id="image0"[^>]+src="([^"]+)"', html)
    if m:
        direct = m.group(1)
    else:
        m = re.search(r'<img[^>]+src="(https?://[^"]+\.jpg)"', html)
        if m:
            direct = m.group(1)
        else:
            return None, None, None
    # Find title (subject)
    m = re.search(r'<title>([^<]+)</title>', html)
    title = m.group(1) if m else ''
    return direct, title, html


def main():
    # Load existing
    existing = set()
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            if row.get('url'):
                existing.add(row['url'])
    print(f'  CSV has {len(existing):,} URLs')

    # Sample countries
    random.seed(123)
    ccs = random.sample(ALL_CC, 30)

    # Get all cam IDs per country
    print(f'\n[Step 1] Scraping {len(ccs)} countries for cam IDs...')
    all_cams = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(scrape_country, cc): cc for cc in ccs}
        for f in as_completed(futs):
            try:
                cams = f.result(timeout=60)
                all_cams.extend(cams)
                if cams:
                    print(f'  {futs[f]}: {len(cams)} cams')
            except Exception as e:
                print(f'  {futs[f]}: ERR {e}')

    print(f'\n  Total cam IDs found: {len(all_cams)}')

    # Visit each cam page to get direct URL
    print(f'\n[Step 2] Visiting each cam page for direct URLs...')
    direct_urls = []
    with ThreadPoolExecutor(max_workers=20) as ex:
        def visit(cam):
            direct, title, html = get_direct_url(cam['id'])
            if direct:
                return {**cam, 'direct': direct, 'title': title}
            return None

        futs = {ex.submit(visit, c): c for c in all_cams}
        n_done = 0
        for f in as_completed(futs):
            try:
                r = f.result(timeout=15)
                if r:
                    direct_urls.append(r)
            except Exception as e:
                pass
            n_done += 1
            if n_done % 50 == 0:
                print(f'  {n_done}/{len(all_cams)} visited, {len(direct_urls)} URLs')

    print(f'\n  Total direct URLs: {len(direct_urls)}')

    # Filter
    new = [d for d in direct_urls if d['direct'] not in existing]
    print(f'  New (not in CSV): {len(new)}')

    # Save
    with open('insecam_country_results.json', 'w', encoding='utf-8') as f:
        json.dump(direct_urls, f, indent=2, ensure_ascii=False)
    print(f'  Saved to insecam_country_results.json')

    if new:
        print(f'\nFirst 30 new URLs:')
        for d in new[:30]:
            print(f'  {d["country"]}: {d["direct"][:80]}')


if __name__ == '__main__':
    main()
