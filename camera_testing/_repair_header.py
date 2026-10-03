"""Repair CSV by reconstructing the header line.

The header line has 3.8MB of null bytes and garbage, but lines 1+ are real data.
This script:
1. Reads line 0, removes null bytes, finds the real header
2. Saves back with proper header
"""
import csv
import os
import re
import sys

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
BACKUP_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\backups\controllable_Webcams_header_corrupt.csv'

csv.field_size_limit(2**31 - 1)
PROPER_HEADER = ['idx', 'project_name', 'url', 'live_stream_url', 'type', 'auth_required', 'auth_user', 'auth_pass', 'enabled', 'live_status', 'http_status', 'content_type', 'server_header', 'page_title', 'description', 'category', 'likely_subject', 'brand', 'model', 'country', 'region', 'city', 'zip', 'address', 'lat', 'lon', 'geo_source', 'isp', 'org', 'asn', 'reverse_dns', 'host', 'confidence', 'notes', 'csv_id']

# Read raw
with open(CSV_PATH, 'rb') as f:
    raw = f.read()
print(f'raw size: {len(raw):,}')
# Find the BOM at start (UTF-8 BOM is EF BB BF)
bom = b'\xef\xbb\xbf'
if raw.startswith(bom):
    raw = raw[3:]
    print('stripped BOM')

# Strip null bytes
clean = raw.replace(b'\x00', b'')
print(f'after null strip: {len(clean):,}')

# Find first newline
idx = clean.find(b'\r\n')
if idx < 0:
    idx = clean.find(b'\n')
print(f'first newline at: {idx}')
header_str = clean[:idx].decode('utf-8', errors='replace')
print(f'header str length: {len(header_str)}')
print(f'header preview: {header_str[:300]}')

# Is this a valid CSV header?
reader = csv.reader([header_str])
fields = next(reader)
print(f'fields: {len(fields)}')
print(f'fields: {fields[:10]}...')

# If header has <35 fields, use PROPER_HEADER
if len(fields) < 35:
    print('header corrupt, using proper header')
    header_line = ','.join(PROPER_HEADER)
    # Get rest of clean data after first newline
    rest = clean[idx+1:]
    if clean[idx:idx+2] == b'\r\n':
        rest = clean[idx+2:]
    else:
        rest = clean[idx+1:]
    new_raw = (b'\xef\xbb\xbf' + header_line.encode('utf-8') + b'\r\n' + rest)
else:
    print('header valid, just remove null bytes')
    # Find first newline in clean, take everything after it
    if clean[idx:idx+2] == b'\r\n':
        rest = clean[idx+2:]
    else:
        rest = clean[idx+1:]
    new_raw = b'\xef\xbb\xbf' + header_str.encode('utf-8').replace(b'\r', b'').replace(b'\n', b'')[:0] + clean[idx+1:] if False else (b'\xef\xbb\xbf' + clean)

# Backup
os.makedirs(os.path.dirname(BACKUP_PATH), exist_ok=True)
with open(BACKUP_PATH, 'wb') as f:
    f.write(raw)
print(f'backed up to {BACKUP_PATH}')

# Save fixed
tmp = CSV_PATH + '.tmp'
with open(tmp, 'wb') as f:
    f.write(new_raw)
import os as _os
for _ in range(10):
    try:
        _os.replace(tmp, CSV_PATH)
        break
    except PermissionError:
        import time; time.sleep(0.5)
print(f'fixed CSV: {len(new_raw):,} bytes')

# Verify
csv.field_size_limit(131072)
with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
    rows = list(csv.reader(f))
print(f'rows: {len(rows)}')
print(f'header cols: {len(rows[0])}')
