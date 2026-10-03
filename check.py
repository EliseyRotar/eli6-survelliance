"""Check pipeline state."""
import csv, os, time
from collections import Counter

csv.field_size_limit(2**31 - 1)
p = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
size = os.path.getsize(p) / 1024 / 1024
mtime = time.ctime(os.path.getmtime(p))
age = time.time() - os.path.getmtime(p)
print(f'Master CSV: {size:.1f} MB, last modified: {mtime} ({age:.0f}s ago)')

with open(p, 'r', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))
print(f'Rows: {len(rows):,}')

# Sources
sources = Counter(r.get('project_name') or '' for r in rows)
print('\nTop project_name:')
for s, c in sources.most_common(20):
    label = s if s else '<empty>'
    print(f'  {label}: {c:,}')

# Brands
brands = Counter(r.get('brand') or '' for r in rows)
print('\nTop brands:')
for b, c in brands.most_common(10):
    label = b if b else '<empty>'
    print(f'  {label}: {c:,}')

# Video streams
video = sum(1 for r in rows if (r.get('type') or '') in ('video', 'video-mjpeg', 'video-h264', 'video-h264-rtsp', 'video-h264-mp4'))
image = sum(1 for r in rows if (r.get('type') or '') == 'image')
print(f'\nStream types: video={video:,}, image={image:,}')
