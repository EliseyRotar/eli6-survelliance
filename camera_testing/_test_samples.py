"""Test that random cams from each source are actually playable."""
import csv
import random
import re
import sys
import time
import urllib.request

csv.field_size_limit(2**31 - 1)

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'


def safe_print(s):
    """Print with Unicode replacement for Windows console."""
    try:
        print(s)
    except UnicodeEncodeError:
        print(s.encode('ascii', 'replace').decode())


def get_source(notes):
    if not notes:
        return 'unknown'
    m = re.search(r'(\w+)_id=', notes)
    return m.group(1) if m else 'unknown'


def test_url(url, timeout=10):
    try:
        req = urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'Mozilla/5.0'})
        r = urllib.request.urlopen(req, timeout=timeout)
        return r.status, len(r.read())
    except urllib.error.HTTPError as e:
        return e.code, 0
    except Exception as e:
        return 'err', str(e)[:30]


def main():
    random.seed(42)
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        rows = list(csv.reader(f))

    # Group rows by source
    by_source = {}
    for i, r in enumerate(rows[1:], 1):
        if len(r) < 35:
            continue
        src = get_source(r[33])
        if src not in by_source:
            by_source[src] = []
        by_source[src].append((i, r))

    sources = sorted(by_source.keys(), key=lambda s: -len(by_source[s]))
    sources = sources[:8]

    safe_print('Testing random cams from top sources...\n')
    total_ok = 0
    total_dead = 0
    for src in sources:
        cams = by_source[src]
        samples = random.sample(cams, min(3, len(cams)))
        safe_print(f'\n=== {src} ({len(cams):,} cams) ===')
        for i, r in samples:
            url = r[3]
            fmt = 'HLS' if '.m3u8' in url.lower() else 'MP4' if '.mp4' in url.lower() else 'MJPG' if 'mjpg' in url.lower() else 'JPG'
            status, _ = test_url(url)
            name = r[1][:50] if len(r) > 1 else ''
            safe_print(f'  [{i}] {fmt:>4} {status:<5} {name}')
            safe_print(f'           {url[:100]}')
            if isinstance(status, int) and status < 400:
                total_ok += 1
            else:
                total_dead += 1
    safe_print(f'\n\nTotal OK: {total_ok}, Total Dead/Error: {total_dead}')


if __name__ == '__main__':
    main()
