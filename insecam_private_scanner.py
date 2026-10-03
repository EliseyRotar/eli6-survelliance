"""Scan insecam.org for private cams by country.

insecam.org has thousands of private cams with default creds.
Already have a script but it's slow. Make a fast version.
"""
import os
import re
import time
import json
import urllib.request
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Private insecam has cams organized by country and city
# We scrape the listing pages, then verify the cams

COUNTRY_CODES = [
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
    'MN', 'BT', 'MV', 'PY', 'UY', 'GY', 'SR', 'GF',
]


def fetch(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64) AppleWebKit/537.36'})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b''
    except Exception:
        return -1, b''


def scrape_insecam_by_type(cam_type, max_pages=10):
    """Scrape cams from insecam.org by type (brand)."""
    found = []
    for page in range(1, max_pages + 1):
        url = f'https://www.insecam.org/en/bytype/{cam_type}/?page={page}'
        status, body = fetch(url)
        if status != 200:
            break
        try:
            html = body.decode('utf-8', errors='replace')
        except:
            break
        cams = []
        # Find direct cam URLs
        for m in re.finditer(r'href="(/en/view/(\d+)/?)"', html):
            cam_id = m.group(2)
            cams.append(cam_id)
        # Also look for direct stream URLs
        for m in re.finditer(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html, re.I):
            found.append(m.group(1))
        for m in re.finditer(r'(https?://[^\s"\'<>]+/mjpg[^\s"\'<>]*)', html, re.I):
            found.append(m.group(1))
        if not cams and not found:
            break
        for cid in cams:
            cam_url = f'https://www.insecam.org/en/view/{cid}/'
            # Visit the page to get direct URL
            s, b = fetch(cam_url)
            if s == 200:
                try:
                    h = b.decode('utf-8', errors='replace')
                    # Find direct image URL
                    m = re.search(r'<img[^>]+id="image0"[^>]+src="([^"]+)"', h)
                    if m:
                        found.append(m.group(1))
                except:
                    pass
        time.sleep(0.5)
    return found


def scrape_insecam_by_country(country, max_pages=5):
    """Scrape cams by country."""
    found = []
    for page in range(1, max_pages + 1):
        url = f'https://www.insecam.org/en/bycountry/{country}/?page={page}'
        status, body = fetch(url)
        if status != 200:
            break
        try:
            html = body.decode('utf-8', errors='replace')
        except:
            break
        cams = []
        for m in re.finditer(r'href="(/en/view/(\d+)/?)"', html):
            cams.append(m.group(2))
        for m in re.finditer(r'(https?://[^\s"\'<>]+\.jpg[^\s"\'<>]*)', html, re.I):
            found.append(m.group(1))
        if not cams:
            break
        for cid in cams:
            cam_url = f'https://www.insecam.org/en/view/{cid}/'
            s, b = fetch(cam_url)
            if s == 200:
                try:
                    h = b.decode('utf-8', errors='replace')
                    m = re.search(r'<img[^>]+id="image0"[^>]+src="([^"]+)"', h)
                    if m:
                        found.append(m.group(1))
                except:
                    pass
        time.sleep(0.5)
    return found


def main():
    out_file = r'C:\Users\eli6-admin\Documents\eli6-surveillance\insecam_private.json'

    # Scrape top countries
    all_found = set()
    for cc in COUNTRY_CODES:
        try:
            cams = scrape_insecam_by_country(cc, max_pages=2)
            for c in cams:
                all_found.add(c)
            print(f'  {cc}: {len(cams)} cams (total: {len(all_found)})', flush=True)
        except Exception as e:
            print(f'  {cc} err: {e}', flush=True)
        time.sleep(1)

    # Also scrape by popular types
    for cam_type in ['axis', 'hikvision', 'dahua', 'foscam', 'mobotix']:
        try:
            cams = scrape_insecam_by_type(cam_type, max_pages=3)
            for c in cams:
                all_found.add(c)
            print(f'  {cam_type}: {len(cams)} cams (total: {len(all_found)})', flush=True)
        except Exception as e:
            print(f'  {cam_type} err: {e}', flush=True)
        time.sleep(1)

    # Save
    with open(out_file, 'w') as f:
        json.dump(sorted(all_found), f, indent=2)
    print(f'Saved {len(all_found)} cam URLs to {out_file}', flush=True)


if __name__ == '__main__':
    main()
