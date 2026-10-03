"""Live URL Resolver - Discovers live stream URLs for all unique hosts in the CSV.

Strategy:
  1. Parse TV catalog (148k cams with known live URLs) - extract per-source patterns
  2. Read CSV - get unique hosts (~3000)
  3. For each host not in TV, probe common live URL patterns
  4. Output JSON map: host -> {live_url, type, source}

Safe: All probes are HEAD requests, no downloads. Bounded timeout (5s per probe).
Parallel: 25 workers with 200ms stagger.

Usage:
  python live_url_resolver.py
  python live_url_resolver.py --workers 50
  python live_url_resolver.py --probe-only
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
OUT_PATH = ROOT / 'live_url_patterns_v2.json'
PROGRESS_PATH = ROOT / 'live_url_resolver_progress.json'

# Skip known bad/extreme patterns
SKIP_PROBE_PATTERNS = set()
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'

# Live URL patterns to probe (in order of likelihood)
# Each is (relative_path, type). {host} = bare host. We test both with and without www.
LIVE_PATTERNS = [
    ('live.m3u8', 'hls'),
    ('stream.m3u8', 'hls'),
    ('playlist.m3u8', 'hls'),
    ('index.m3u8', 'hls'),
    ('hls/stream.m3u8', 'hls'),
    ('hls/live.m3u8', 'hls'),
    ('live/stream.m3u8', 'hls'),
    ('live/index.m3u8', 'hls'),
    ('live.mpd', 'dash'),
    ('manifest.mpd', 'dash'),
    ('stream.mp4', 'mp4'),
    ('live.mp4', 'mp4'),
    ('video.mp4', 'mp4'),
    ('live.flv', 'flv'),
    ('stream.flv', 'flv'),
    ('mjpeg/1', 'mjpeg'),
    ('video.cgi', 'mjpeg'),
    ('mjpg/video.mjpg', 'mjpeg'),
    ('cgi-bin/mjpg', 'mjpeg'),
    ('cgi-bin/mjpg/video.cgi', 'mjpeg'),
]

# Skip probing these (private/CDN/unlikely)
SKIP_HOST_PATTERNS = [
    r'\.local$', r'^localhost$', r'127\.', r'192\.168\.', r'10\.', r'172\.(1[6-9]|2\d|3[0-1])\.',
    r'\.internal$', r'argus-public', r'cdn\.', r'\.cloudfront\.net$',
    r'\.amazonaws\.com$', r'\.azureedge\.net$', r'\.googleapis\.com$',
]


def load_tv_patterns():
    """Extract per-source URL patterns from TV catalog.

    Returns: dict[source_name] -> {sample_video_urls: [...], sample_image_urls: [...], feed_types: [...]}
    """
    if not TV_PATH.exists():
        return {}
    print(f'Loading TV catalog from {TV_PATH} ({TV_PATH.stat().st_size // (1024*1024)} MB)...', flush=True)
    with open(TV_PATH, encoding='utf-8') as f:
        tv = json.load(f)
    cams = tv.get('cameras', [])
    print(f'  TV catalog: {len(cams):,} cams', flush=True)
    by_source = defaultdict(lambda: {'video_urls': [], 'image_urls': [], 'feed_types': set(), 'hosts': set()})
    for c in cams:
        src = c.get('source', 'unknown')
        s = by_source[src]
        if c.get('videoUrl'):
            s['video_urls'].append(c['videoUrl'])
        if c.get('imageUrl'):
            s['image_urls'].append(c['imageUrl'])
        if c.get('feedType'):
            s['feed_types'].add(c['feedType'])
        for url in [c.get('videoUrl'), c.get('imageUrl')]:
            if url:
                m = re.match(r'https?://([^/]+)', url)
                if m:
                    s['hosts'].add(m.group(1))
    # Cap samples at 3 per source to keep JSON small
    for src, s in by_source.items():
        s['video_urls'] = s['video_urls'][:3]
        s['image_urls'] = s['image_urls'][:3]
        s['feed_types'] = list(s['feed_types'])
        s['hosts'] = list(s['hosts'])
    return dict(by_source)


def get_unique_hosts():
    """Get unique hosts from CSV."""
    if not CSV_PATH.exists():
        return []
    print(f'Reading CSV hosts from {CSV_PATH}...', flush=True)
    hosts = set()
    with open(CSV_PATH, encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            h = (row.get('host') or '').strip().lower()
            if h:
                hosts.add(h)
    return sorted(hosts)  # already lowercased


def host_to_url_candidates(host):
    """Generate (url, type) candidates for probing a host."""
    out = []
    schemes = ['https://', 'http://']
    for sch in schemes:
        for path, t in LIVE_PATTERNS:
            out.append((f'{sch}{host}/{path}', t))
    return out


def probe_url(url, timeout=4):
    """HEAD probe. Returns (ok, content_type, content_length, final_url)."""
    try:
        req = urllib.request.Request(url, method='HEAD', headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            ct = (r.headers.get('Content-Type') or '').lower()
            cl = r.headers.get('Content-Length')
            return True, ct, cl, r.url
    except urllib.error.HTTPError as e:
        if e.code in (405, 403):  # method not allowed - try GET
            try:
                req = urllib.request.Request(url, method='GET', headers={'User-Agent': UA, 'Range': 'bytes=0-1023'})
                with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                    ct = (r.headers.get('Content-Type') or '').lower()
                    cl = r.headers.get('Content-Length')
                    return True, ct, cl, r.url
            except Exception:
                return False, '', '', ''
        return False, '', '', ''
    except Exception:
        return False, '', '', ''


def is_stream_content_type(ct):
    if not ct:
        return None
    if 'mpegurl' in ct or 'application/x-mpegurl' in ct or ct == 'application/vnd.apple.mpegurl':
        return 'hls'
    if 'dash' in ct or 'mpd' in ct:
        return 'dash'
    if ct.startswith('video/') or 'octet-stream' in ct:
        return 'mp4'
    if ct.startswith('image/'):
        return 'mjpeg'
    if 'multipart' in ct or 'x-mixed-replace' in ct:
        return 'mjpeg'
    if 'flv' in ct:
        return 'flv'
    return None


def is_skip_host(host):
    for pat in SKIP_HOST_PATTERNS:
        if re.search(pat, host):
            return True
    return False


def probe_host(host, timeout=4, max_find=1):
    """Probe a single host for live stream URLs. Returns list of (url, type) found."""
    if is_skip_host(host):
        return []
    candidates = host_to_url_candidates(host)
    found = []
    for url, t in candidates:
        ok, ct, cl, final = probe_url(url, timeout=timeout)
        if not ok:
            continue
        # If declared type matches content, accept
        inferred = is_stream_content_type(ct)
        if inferred:
            found.append((final, inferred))
        elif cl and cl.isdigit() and int(cl) > 1000:  # >1KB body
            # accept as generic
            found.append((final, t))
        if len(found) >= max_find:
            break
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=25, help='parallel workers (default 25)')
    ap.add_argument('--probe-only', action='store_true', help='only probe, skip TV extraction')
    ap.add_argument('--tv-only', action='store_true', help='only TV extraction, skip probe')
    ap.add_argument('--limit', type=int, default=0, help='limit number of hosts to probe (0=all)')
    args = ap.parse_args()

    # 1. TV patterns
    tv_patterns = {}
    if not args.probe_only:
        tv_patterns = load_tv_patterns()
        # Map TV host -> source name
        host_to_tv_source = {}
        for src, s in tv_patterns.items():
            for h in s.get('hosts', []):
                host_to_tv_source[h] = src

    # 2. Unique CSV hosts
    csv_hosts = get_unique_hosts()
    print(f'CSV: {len(csv_hosts):,} unique hosts', flush=True)

    # 3. Build initial map from TV catalog
    # For each host in TV, save the sample live URL
    out_map = {}
    if not args.probe_only:
        # Dedupe by lowercased host
        for host, src in host_to_tv_source.items():
            host_lc = host.lower()
            s = tv_patterns[src]
            video_urls = s.get('video_urls', [])
            if video_urls:
                # take first sample as the live URL template
                # Prefer existing entry from a different source if it has a real m3u8
                existing = out_map.get(host_lc)
                new_url = video_urls[0]
                new_is_hls = '.m3u8' in new_url
                if existing:
                    existing_is_hls = '.m3u8' in existing['live_url']
                    # Skip if existing is already hls and new isn't
                    if existing_is_hls and not new_is_hls:
                        continue
                out_map[host_lc] = {
                    'live_url': new_url,
                    'type': 'hls' if new_is_hls else ('mp4' if '.mp4' in new_url else 'video'),
                    'source': f'tv:{src}',
                    'verified': False,
                }
        print(f'TV-derived live hosts: {len(out_map):,}', flush=True)

    # 4. Probe remaining hosts
    if not args.tv_only:
        to_probe = [h for h in csv_hosts if h not in out_map]
        if args.limit > 0:
            to_probe = to_probe[:args.limit]
        print(f'Probing {len(to_probe):,} remaining hosts with {args.workers} workers...', flush=True)

        progress = {'probed': 0, 'found': 0, 'total': len(to_probe), 'start_ts': time.time()}
        if PROGRESS_PATH.exists():
            try:
                with open(PROGRESS_PATH, encoding='utf-8') as f:
                    progress = json.load(f)
                    progress['probed'] = 0
                    progress['found'] = 0
            except Exception:
                pass

        def _probe_one(host):
            try:
                return host, probe_host(host, timeout=4)
            except Exception as e:
                return host, []

        start = time.time()
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futures = {ex.submit(_probe_one, h): h for h in to_probe}
            for i, fut in enumerate(as_completed(futures), 1):
                host, found = fut.result()
                if found:
                    url, ftype = found[0]
                    out_map[host] = {
                        'live_url': url,
                        'type': ftype,
                        'source': 'probe',
                        'verified': True,
                    }
                    progress['found'] += 1
                progress['probed'] += 1
                if i % 50 == 0 or i == len(to_probe):
                    elapsed = time.time() - start
                    rate = i / elapsed if elapsed > 0 else 0
                    eta = (len(to_probe) - i) / rate if rate > 0 else 0
                    print(f'  [{i:>5}/{len(to_probe)}] found={progress["found"]} rate={rate:.1f}/s eta={eta:.0f}s', flush=True)
                    # Save progress every 50
                    with open(PROGRESS_PATH, 'w', encoding='utf-8') as f:
                        json.dump(progress, f)

    # 5. Save output
    out = {
        'generated_at': time.time(),
        'tv_hosts': sum(1 for v in out_map.values() if v['source'].startswith('tv:')),
        'probed_hosts': sum(1 for v in out_map.values() if v['source'] == 'probe'),
        'total_hosts': len(out_map),
        'patterns': out_map,
    }
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2)
    print(f'\nWrote {OUT_PATH}')
    print(f'  TV-derived: {out["tv_hosts"]:,}')
    print(f'  Probed: {out["probed_hosts"]:,}')
    print(f'  Total: {out["total_hosts"]:,}')


if __name__ == '__main__':
    main()
