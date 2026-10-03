"""Scan HLS cams to find a working poster URL (jpegs with same name pattern).

For each HLS cam in our CSV, try common poster filename variants via
HEAD requests through /api/proxy/img. If any returns 200 with image content,
save the working URL as `poster_url` in a separate file.

We can't update the CSV directly (no poster_url column), so we'll write
a JSON map: cam_idx -> poster_url
"""
import csv
import json
import os
import sys
import time
import urllib.request
import urllib.parse
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(line_buffering=True)

CSV_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')
PROXY = 'http://127.0.0.1:8773/api/proxy/img'

# Output: a JSON map of cam_idx -> poster_url
OUT = Path(r'C:\Users\eli6-admin\AppData\Local\Temp\poster_urls.json')
PROGRESS = Path(r'C:\Users\eli6-admin\AppData\Local\Temp\poster_progress.json')

# Common poster name patterns to try (in priority order)
POSTER_PATTERNS = [
    '{base}.jpg',           # most common: playlist.m3u8 -> playlist.jpg
    '{base}_thumb.jpg',
    '{base}-thumb.jpg',
    '{dir}/thumb.jpg',
    '{dir}/preview.jpg',
    '{dir}/latest.jpg',
    '{dir}/snap.jpg',
    '{dir}/image.jpg',
    '{dir}/still.jpg',
    '{dir}/poster.jpg',
    '{base}_640x360.jpg',
    '{base}_small.jpg',
    '{dir}/0.jpg',          # some cam servers use numbered frames
    '{dir}/1.jpg',
]

def make_patterns(hls_url):
    """Generate candidate poster URLs for a given HLS URL."""
    if not hls_url:
        return []
    # Strip query string
    base_full = hls_url.split('?')[0]
    # Get the file base (without .m3u8)
    m = re.match(r'^(.+?)/([^/]+?)(?:\.m3u8)?$', base_full)
    if not m:
        return []
    dir_path = m.group(1)
    file_base = m.group(2)
    # Strip _h, _l suffixes if present (divas pattern)
    file_base = re.sub(r'_[lh]$', '', file_base)
    candidates = []
    for pat in POSTER_PATTERNS:
        candidates.append(pat.format(base=file_base, dir=dir_path))
    # Add common static URLs
    candidates.append(f'{dir_path}/latest.jpg')
    candidates.append(f'{dir_path}/current.jpg')
    candidates.append(f'{dir_path}/frame.jpg')
    return candidates

def check_poster(hls_url, idx):
    """Try all poster patterns for a single HLS URL. Return the first working one."""
    if not hls_url or '.m3u8' not in hls_url:
        return idx, None
    candidates = make_patterns(hls_url)
    for path in candidates[:6]:  # test up to 6 candidates
        if not path.startswith('http'):
            continue
        proxy_url = f'{PROXY}?u={urllib.parse.quote(path, safe="")}'
        try:
            req = urllib.request.Request(proxy_url, method='HEAD', headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            })
            with urllib.request.urlopen(req, timeout=3) as r:
                ct = r.headers.get('Content-Type', '')
                cl = int(r.headers.get('Content-Length', '0') or 0)
                if r.status == 200 and ct.startswith('image/') and cl > 500:
                    return idx, path
        except Exception:
            continue
    return idx, None

def main():
    # Load existing poster URLs
    poster_urls = {}
    if OUT.exists():
        try:
            with open(OUT, encoding='utf-8') as f:
                poster_urls = json.load(f)
        except Exception:
            pass
    print(f'Loaded {len(poster_urls)} existing poster URLs')

    # Load HLS cams from CSV
    hls_cams = []
    with open(CSV_PATH, encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get('type') == 'hls' and r.get('live_stream_url'):
                hls_cams.append((r['idx'], r['live_stream_url']))
    print(f'Found {len(hls_cams)} HLS cams in CSV')

    # Filter out already-scanned
    to_scan = [(idx, url) for idx, url in hls_cams if idx not in poster_urls]
    print(f'To scan: {len(to_scan)} (skipping {len(hls_cams) - len(to_scan)} already known)')

    if not to_scan:
        return

    # Save progress periodically
    found = 0
    t0 = time.time()
    scanned = 0

    # Use thread pool for concurrent HEAD requests
    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(check_poster, url, idx): idx for idx, url in to_scan}
        for fut in as_completed(futures):
            idx, poster = fut.result()
            scanned += 1
            if poster:
                poster_urls[idx] = poster
                found += 1
            if scanned % 100 == 0:
                elapsed = time.time() - t0
                rate = scanned / elapsed if elapsed > 0 else 0
                print(f'  {scanned}/{len(to_scan)} scanned, {found} found, {rate:.1f}/s, {elapsed:.0f}s', flush=True)
                with open(OUT, 'w', encoding='utf-8') as f:
                    json.dump(poster_urls, f, ensure_ascii=False)

    # Final save
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(poster_urls, f, ensure_ascii=False)
    elapsed = time.time() - t0
    print(f'\nDone: {scanned} scanned, {found} posters found in {elapsed:.0f}s')

if __name__ == '__main__':
    main()
