"""Scrape landing pages from the 1,670 missing TV cams to find direct cam URLs.

We try:
- fintraffic.fi
- traintrackerapp.com/railcams
- allsky7.net
- any other unique sourceUrl

For each landing page, find image/video URLs that look like direct cam URLs.
"""
import json
import csv
import re
import os
import sys
import time
import urllib.request
import ssl
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

sys.stdout.reconfigure(line_buffering=True)

WORK_DIR = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
CSV_PATH = os.path.join(WORK_DIR, 'controllable_Webcams.csv')
MISSING_PATH = os.path.join(WORK_DIR, 'tv_missing.json')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def fetch(url, timeout=10):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64) AppleWebKit/537.36'})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, r.read(2*1024*1024).decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        return e.code, ''
    except Exception as e:
        return -1, ''


def extract_image_urls(html, base_host):
    """Find image/jpg/mjpg URLs in HTML."""
    urls = set()
    # Common patterns
    patterns = [
        r'(https?://[^\s"\'<>]+\.jpg)',
        r'(https?://[^\s"\'<>]+\.jpeg)',
        r'(https?://[^\s"\'<>]+\.png)',
        r'(https?://[^\s"\'<>]+/mjpg/[^\s"\'<>]+)',
        r'(https?://[^\s"\'<>]+/video\.mjpg)',
        r'(https?://[^\s"\'<>]+/axis-cgi/[^\s"\'<>]+)',
        r'(https?://[^\s"\'<>]+/cgi-bin/[^\s"\'<>]+\.cgi)',
        r'(https?://[^\s"\'<>]+/Streaming/[^\s"\'<>]+)',
        r'(https?://[^\s"\'<>]+\.m3u8)',
        r'(https?://[^\s"\'<>]+\.mp4)',
        r'(https?://[^\s"\'<>]+/cam[_\d]*\.cgi)',
    ]
    for p in patterns:
        for m in re.finditer(p, html, re.I):
            urls.add(m.group(1))
    return urls


def main():
    csv.field_size_limit(2**31 - 1)

    with open(MISSING_PATH) as f:
        missing = json.load(f)

    # Get unique source URLs
    src_urls = set()
    for c in missing:
        su = c.get('sourceUrl', '')
        if su:
            src_urls.add(su)
    print(f'Unique source URLs to scrape: {len(src_urls)}', flush=True)

    # Build cam_id -> sourceUrl map
    cam_to_url = {}
    for c in missing:
        su = c.get('sourceUrl', '')
        if su:
            cam_to_url.setdefault(su, []).append(c)

    # For each source URL, scrape the page and find image URLs
    found_urls = {}  # source_url -> set of direct image URLs
    for src_url in src_urls:
        host = re.match(r'https?://([^/]+)', src_url).group(1)
        m = re.match(r'https?://(?:www\.)?([^/]+)', src_url)
        host = m.group(1) if m else src_url
        print(f'  {host}...', flush=True, end=' ')
        status, html = fetch(src_url, timeout=10)
        if status != 200:
            print(f'failed (status {status})', flush=True)
            continue
        urls = extract_image_urls(html, host)
        found_urls[src_url] = urls
        print(f'found {len(urls)} image URLs', flush=True)
        time.sleep(0.5)

    # Save
    with open('tv_missing_scrape.json', 'w') as f:
        json.dump({k: list(v) for k, v in found_urls.items()}, f, indent=2)
    print(f'\nSaved to tv_missing_scrape.json', flush=True)

    # Show stats
    total_urls = sum(len(v) for v in found_urls.values())
    print(f'Total direct URLs found: {total_urls:,}', flush=True)

    # Sample
    for src, urls in list(found_urls.items())[:5]:
        print(f'\n{src}:')
        for u in list(urls)[:5]:
            print(f'  {u}')


if __name__ == '__main__':
    main()
