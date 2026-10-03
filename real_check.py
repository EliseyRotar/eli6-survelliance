"""Real check of CSV state."""
import csv, os, time

csv.field_size_limit(2**31 - 1)
csv_path = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'

size = os.path.getsize(csv_path) / 1024 / 1024
mtime = time.ctime(os.path.getmtime(csv_path))
age = time.time() - os.path.getmtime(csv_path)
print(f'Master CSV: {size:.1f} MB')
print(f'Last modified: {mtime} ({age:.0f}s ago)')

with open(csv_path, 'r', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

print(f'Rows: {len(rows):,}')
print('First 3:')
for r in rows[:3]:
    url = r.get('url') or '[NONE]'
    print(f'  {url[:80]}')
print('Last 3:')
for r in rows[-3:]:
    url = r.get('url') or '[NONE]'
    print(f'  {url[:80]}')

# Ruse cams
ruse = [r for r in rows if (r.get('project_name') or '') in ('ruse', 'ruse_v2', 'ruse_scan', 'ruse_ip_cam', 'ruse_isp_scan')]
print(f'\nRuse cams: {len(ruse)}')

# Brand coverage
from collections import Counter
brands = Counter(r.get('brand') or '' for r in rows)
top = [(b or '<empty>', c) for b, c in brands.most_common(10)]
print(f'\nTop brands:')
for b, c in top:
    print(f'  {b}: {c:,}')
