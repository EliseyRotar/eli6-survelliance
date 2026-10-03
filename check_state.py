"""Pipeline state check."""
import csv, os, time
from collections import Counter

csv.field_size_limit(2**31 - 1)

# Find CSV
import glob
p = None
for f in glob.glob(r'C:\Users\eli6-admin\Documents\**/controllable_Webcams.csv', recursive=True):
    p = f
    break

if not p or not os.path.exists(p):
    print('CSV not found')
    exit(1)

print(f'CSV: {p}')
size = os.path.getsize(p) / 1024 / 1024
mtime = time.ctime(os.path.getmtime(p))
age = time.time() - os.path.getmtime(p)
print(f'Size: {size:.1f} MB, last modified: {mtime} ({age:.0f}s ago)')

with open(p, 'r', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))
print(f'Rows: {len(rows):,}')

types = Counter(r.get('type') or '' for r in rows)
print(f'\nStream types:')
for t, c in types.most_common(10):
    print(f'  {t if t else "<empty>"}: {c:,}')

# RTSP
rtsp = sum(1 for r in rows if (r.get('url') or '').startswith('rtsp://'))
print(f'\nRTSP cams: {rtsp:,}')

# Video
video = sum(1 for r in rows if (r.get('type') or '').startswith('video'))
print(f'Video streams: {video:,}')

# Live
live = sum(1 for r in rows if (r.get('live_status') or '') == 'live')
print(f'Live: {live:,}')
auth = sum(1 for r in rows if (r.get('live_status') or '') == 'auth_required')
print(f'Auth-required: {auth:,}')

# Ruse
ruse_names = ('ruse', 'ruse_v2', 'ruse_scan', 'ruse_ip_cam', 'ruse_isp_scan', 'ruse_restored')
ruse = [r for r in rows if (r.get('project_name') or '') in ruse_names]
print(f'\nRuse cams: {len(ruse)}')
for r in ruse:
    url = r.get('url', '')[:80]
    pn = r.get('project_name', '')
    print(f'  [{pn}] {url}')
