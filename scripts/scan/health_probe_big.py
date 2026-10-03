"""Larger sample — 200 cams per source for health check."""
import csv
import random
import urllib.request
import urllib.error
import socket
import time
from collections import defaultdict, Counter

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'

def head_url(url, timeout=4):
    try:
        req = urllib.request.Request(url, method='HEAD')
        req.add_header('User-Agent', 'Mozilla/5.0')
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.headers.get('Content-Type', '')
    except urllib.error.HTTPError as e:
        return e.code, ''
    except (urllib.error.URLError, socket.timeout, ConnectionResetError) as e:
        return 'ERR', str(e)[:40]
    except Exception as e:
        return 'ERR', str(e)[:40]

with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
    rows = list(csv.reader(f))

print(f'total rows: {len(rows)-1}')

# Group by source
by_source = defaultdict(list)
for r in rows[1:]:
    if len(r) > 33:
        src = r[33].split('source=')[1].split(',')[0].split(';')[0] if 'source=' in r[33] else 'no-source'
        by_source[src].append(r)

print(f'\nSource distribution:')
for src, lst in sorted(by_source.items(), key=lambda x: -len(x[1])):
    print(f'  {src}: {len(lst)} rows')

# Sample 30 from each source
random.seed(456)
print(f'\n--- Health check (30 per source) ---')
total_alive = 0
total_probed = 0
total_img = 0
results_per_src = {}
for src, lst in by_source.items():
    if len(lst) < 5:
        continue
    sample = random.sample(lst, min(30, len(lst)))
    alive = 0
    img = 0
    statuses = Counter()
    for r in sample:
        url = r[3] if len(r) > 3 else ''
        if not url:
            continue
        status, ct = head_url(url, timeout=4)
        if isinstance(status, int):
            statuses[status] += 1
            if 200 <= status < 400 or status == 401:
                alive += 1
            if 'image' in ct.lower() or 'multipart' in ct.lower() or 'video' in ct.lower() or 'octet' in ct.lower():
                img += 1
        else:
            statuses['ERR'] += 1
    results_per_src[src] = (alive, len(sample), statuses, img)
    total_alive += alive
    total_probed += len(sample)
    total_img += img

print(f'\nResults per source:')
print(f'{"source":<25} {"alive":<8} {"total":<8} {"rate":<8} {"img":<6}')
print('-' * 60)
for src, (alive, total, statuses, img) in sorted(results_per_src.items(), key=lambda x: -x[1][0]/max(x[1][1],1)):
    rate = alive*100/total if total else 0
    print(f'{src:<25} {alive:<8} {total:<8} {rate:5.1f}% {img:<6}')

print(f'\n=== OVERALL ===')
print(f'Total probed: {total_probed}')
print(f'Total alive (2xx/3xx/401): {total_alive}')
print(f'Alive rate: {total_alive*100/total_probed:.1f}%')
print(f'Confirmed image/video: {total_img} ({total_img*100/total_probed:.1f}%)')
