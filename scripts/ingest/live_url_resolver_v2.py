"""Live URL Resolver v2 - Per-cam URL mapping from TV catalog.

Strategy:
  1. Read TV catalog. For each cam, store (imageUrl, videoUrl) pair.
  2. Read CSV. For each cam, check if its `live_stream_url` matches any TV imageUrl.
  3. If yes, use that TV cam's `videoUrl` as the cam's live stream.
  4. Output JSON map: {csv_cam_idx: live_url} for the dashboard.
  5. Also output a host->template JSON for runtime discovery.
"""
import json
import csv
import os
import re
import sys
import time
import argparse
import urllib.request
import urllib.error
import ssl
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance')
CSV_PATH = ROOT / 'controllable_Webcams.csv'
TV_PATH = ROOT / 'camera_testing' / 'tv_catalog_full.json'
OUT_PATH = ROOT / 'live_cam_mappings_v2.json'
PROGRESS_PATH = ROOT / 'live_resolver_v2_progress.json'

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'


def normalize_url(url):
    """Normalize URL for matching: lowercase host, keep query params, trim trailing slash.

    We KEEP query params because many webcams differentiate cameras via camid=... params.
    """
    if not url:
        return ''
    url = url.strip().lower()
    if '#' in url:
        url = url.split('#', 1)[0]
    return url.rstrip('/')


def extract_uuid(url):
    """Extract the UUID from autostrade-style URLs (e.g. 'a3c36eb0-52b0-404f-ae84-c4f2574c4e79')."""
    if not url:
        return None
    m = re.search(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', url)
    return m.group(1) if m else None


def load_tv_index():
    """Build a TV index: imageUrl_normalized -> videoUrl.

    Also build a UUID index: uuid -> videoUrl (for autostrade cross-ref).
    Returns: (image_to_video, uuid_to_video, cam_count)
    """
    if not TV_PATH.exists():
        return {}, {}, 0
    print(f'Loading TV catalog from {TV_PATH} ({TV_PATH.stat().st_size // (1024*1024)} MB)...', flush=True)
    with open(TV_PATH, encoding='utf-8') as f:
        tv = json.load(f)
    cams = tv.get('cameras', [])
    print(f'  TV catalog: {len(cams):,} cams', flush=True)
    image_to_video = {}
    uuid_to_video = {}
    for c in cams:
        iu = normalize_url(c.get('imageUrl', ''))
        vu = c.get('videoUrl', '')
        if iu and vu:
            image_to_video[iu] = vu
        # Also map by UUID (autostrade pattern)
        iu_uuid = extract_uuid(iu)
        vu_uuid = extract_uuid(vu)
        if iu_uuid and vu_uuid and iu_uuid == vu_uuid:
            uuid_to_video[iu_uuid] = vu
    print(f'  TV imageUrl->videoUrl: {len(image_to_video):,}', flush=True)
    print(f'  TV UUID->videoUrl: {len(uuid_to_video):,}', flush=True)
    return image_to_video, uuid_to_video, len(cams)


def map_csv_cams():
    """Read CSV and produce per-cam live URL mappings.

    Returns: list of (idx, csv_live_url, mapped_live_url, source)
    """
    if not CSV_PATH.exists():
        return []
    image_to_video, uuid_to_video, _ = load_tv_index()
    print(f'Reading CSV from {CSV_PATH}...', flush=True)

    results = []
    matched = 0
    total = 0
    with open(CSV_PATH, encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            idx = row.get('idx', '').strip()
            live = (row.get('live_stream_url') or '').strip()
            host = (row.get('host') or '').strip().lower()
            if not idx or not live:
                continue
            live_norm = normalize_url(live)
            mapped = None
            src = None
            # Try 1: direct imageUrl match (works for any source)
            if live_norm in image_to_video:
                mapped = image_to_video[live_norm]
                src = 'tv:imageurl'
            elif not host.endswith('video.autostrade.it'):
                # Try 2: UUID match (autostrade handled separately by regex)
                # Skip autostrade since view number doesn't match between CSV and TV
                uuid = extract_uuid(live)
                if uuid and uuid in uuid_to_video:
                    mapped = uuid_to_video[uuid]
                    src = 'tv:uuid'
            if mapped:
                results.append((int(idx), live, mapped, src))
                matched += 1
    print(f'  CSV: {total:,} cams, {matched:,} matched to live URLs in TV', flush=True)
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0)
    args = ap.parse_args()

    results = map_csv_cams()
    if args.limit > 0:
        results = results[:args.limit]

    # Build cam_idx -> live_url map
    cam_to_live = {}
    for idx, src_url, mapped_url, src in results:
        cam_to_live[idx] = {
            'live_url': mapped_url,
            'image_url': src_url,
            'source': src,
        }

    out = {
        'generated_at': time.time(),
        'total_mapped': len(cam_to_live),
        'mappings': cam_to_live,
    }
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2)
    print(f'\nWrote {OUT_PATH}')
    print(f'  Total cams with live URLs: {len(cam_to_live):,}')
    # By source
    by_src = defaultdict(int)
    for v in cam_to_live.values():
        by_src[v['source']] += 1
    for src, n in sorted(by_src.items(), key=lambda x: -x[1]):
        print(f'  {src}: {n:,}')


if __name__ == '__main__':
    main()
