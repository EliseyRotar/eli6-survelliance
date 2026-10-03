"""Check pipeline state."""
import csv, os, time
from collections import Counter

csv.field_size_limit(2**31 - 1)
p = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
print(f'Path: {p}')
print(f'Exists: {os.path.exists(p)}')

if not os.path.exists(p):
    # Try alternate
    p = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
    print(f'Trying alt: {p} exists={os.path.exists(p)}')
    if not os.path.exists(p):
        # Find the CSV
        for root, dirs, files in os.walk(r'C:\Users\eli6-admin\Documents'):
            for f in files:
                if f == 'controllable_Webcams.csv':
                    p = os.path.join(root, f)
                    print(f'Found: {p}')
                    break
            if 'Found' in str(p):
                break

if not os.path.exists(p):
    print('CSV not found!')
    exit(1)

size = os.path.getsize(p) / 1024 / 1024
mtime = time.ctime(os.path.getmtime(p))
age = time.time() - os.path.getmtime(p)
print(f'Master CSV: {size:.1f} MB, last modified: {mtime} ({age:.0f}s ago)')

with open(p, 'r', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))
print(f'Rows: {len(rows):,}')

sources = Counter(r.get('project_name') or '' for r in rows)
print('\nTop project_name:')
for s, c in sources.most_common(20):
    label = s if s else '<empty>'
    print(f'  {label}: {c:,}')

brands = Counter(r.get('brand') or '' for r in rows)
print('\nTop brands:')
for b, c in brands.most_common(10):
    label = b if b else '<empty>'
    print(f'  {label}: {c:,}')

video = sum(1 for r in rows if (r.get('type') or '') in ('video', 'video-mjpeg', 'video-h264', 'video-h264-rtsp', 'video-h264-mp4'))
image = sum(1 for r in rows if (r.get('type') or '') == 'image')
print(f'\nStream types: video={video:,}, image={image:,}')
