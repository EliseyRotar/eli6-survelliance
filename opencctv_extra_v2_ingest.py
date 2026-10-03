"""
Ingest OpenCCTV extra v2 into CSV.
"""
import csv
import json
from pathlib import Path

CSV = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')
EXTRA = Path(r'C:\Users\eli6-admin\AppData\Local\Temp\opencode\opencctv_extra_v2.json')

# Read CSV header
with open(CSV, encoding='utf-8', newline='') as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = list(reader)
H = {k: i for i, k in enumerate(header)}
print(f'Header has {len(header)} cols, current {len(rows)} rows')

# Build set of existing live URLs for dedup
existing = set()
for r in rows:
    if len(r) > H['live_stream_url']:
        existing.add(r[H['live_stream_url']])

# Load OpenCCTV cams
with open(EXTRA, encoding='utf-8') as f:
    cams = json.load(f)
print(f'Loaded {len(cams)} cams from extra v2')

# Country code to full name
CC = {
    'US': 'United States', 'CA': 'Canada', 'MX': 'Mexico', 'BR': 'Brazil',
    'AR': 'Argentina', 'CL': 'Chile', 'CO': 'Colombia', 'PE': 'Peru',
    'GB': 'United Kingdom', 'IE': 'Ireland', 'FR': 'France', 'ES': 'Spain',
    'PT': 'Portugal', 'IT': 'Italy', 'DE': 'Germany', 'NL': 'Netherlands',
    'BE': 'Belgium', 'LU': 'Luxembourg', 'AT': 'Austria', 'CH': 'Switzerland',
    'PL': 'Poland', 'CZ': 'Czech Republic', 'SK': 'Slovakia', 'HU': 'Hungary',
    'RO': 'Romania', 'BG': 'Bulgaria', 'GR': 'Greece', 'HR': 'Croatia',
    'SI': 'Slovenia', 'RS': 'Serbia', 'UA': 'Ukraine', 'BY': 'Belarus',
    'LT': 'Lithuania', 'LV': 'Latvia', 'EE': 'Estonia', 'FI': 'Finland',
    'SE': 'Sweden', 'NO': 'Norway', 'DK': 'Denmark', 'IS': 'Iceland',
    'RU': 'Russia', 'TR': 'Turkey', 'IL': 'Israel', 'AE': 'UAE',
    'SA': 'Saudi Arabia', 'EG': 'Egypt', 'MA': 'Morocco', 'NG': 'Nigeria',
    'KE': 'Kenya', 'ZA': 'South Africa', 'IN': 'India', 'CN': 'China',
    'TW': 'Taiwan', 'HK': 'Hong Kong', 'JP': 'Japan', 'KR': 'South Korea',
    'MY': 'Malaysia', 'SG': 'Singapore', 'TH': 'Thailand', 'VN': 'Vietnam',
    'PH': 'Philippines', 'ID': 'Indonesia', 'AU': 'Australia', 'NZ': 'New Zealand',
    'PG': 'Papua New Guinea', 'FJ': 'Fiji',
    'KZ': 'Kazakhstan', 'KG': 'Kyrgyzstan', 'UZ': 'Uzbekistan',
}

TYPE_MAP = {
    'm3u8': 'hls',
    'mp4': 'mp4',
    'mjpeg': 'mjpeg',
    'iframe': 'youtube',
    'image': 'image',
}

# Find max idx
max_idx = max(int(r[H['idx']]) for r in rows if r[H['idx']].isdigit())
next_idx = max_idx + 1
print(f'Next idx: {next_idx}')

added = 0
skipped_dup = 0
no_url = 0
for c in cams:
    if not isinstance(c, dict):
        continue
    feed_url = c.get('feed_url', c.get('image_url', ''))
    if not feed_url:
        no_url += 1
        continue
    if feed_url in existing:
        skipped_dup += 1
        continue
    existing.add(feed_url)

    country_code = c.get('country', '') or ''
    country_full = CC.get(country_code, country_code)
    feed_type = c.get('feed_type', 'image') or 'image'
    type_ = TYPE_MAP.get(feed_type, 'image')

    # Build row
    row = [''] * len(header)
    row[H['idx']] = str(next_idx)
    row[H['project_name']] = c.get('name', '') or f"OpenCCTV Cam {c.get('id', '')}"
    row[H['url']] = c.get('url', '') or c.get('homepage', '') or feed_url
    row[H['live_stream_url']] = feed_url
    row[H['type']] = type_
    row[H['auth_required']] = '0'
    row[H['auth_user']] = ''
    row[H['auth_pass']] = ''
    row[H['enabled']] = '1'
    row[H['live_status']] = 'live' if type_ in ('hls', 'mp4', 'mjpeg', 'youtube') else 'unknown'
    row[H['content_type']] = 'application/x-mpegurl' if type_ == 'hls' else 'video/mp4' if type_ == 'mp4' else 'image/jpeg'
    row[H['page_title']] = ''
    row[H['description']] = c.get('description', '') or ''
    row[H['category']] = 'open-data'
    row[H['likely_subject']] = c.get('subject', '') or 'unknown'
    row[H['brand']] = 'OpenCCTV'
    row[H['model']] = c.get('source', c.get('feed_type', '')) or ''
    row[H['country']] = country_full
    row[H['region']] = c.get('state', '') or ''
    row[H['city']] = c.get('city', '') or ''
    row[H['zip']] = ''
    row[H['address']] = c.get('address', '') or c.get('location', '') or ''
    row[H['road']] = ''
    row[H['location_precision']] = 'precise'
    try:
        row[H['lat']] = str(c.get('lat', '')) if c.get('lat') is not None else ''
    except:
        row[H['lat']] = ''
    try:
        row[H['lon']] = str(c.get('lng', c.get('lon', ''))) if c.get('lng', c.get('lon')) is not None else ''
    except:
        row[H['lon']] = ''
    row[H['geo_source']] = 'opencctv'
    row[H['isp']] = ''
    row[H['org']] = ''
    row[H['asn']] = ''
    row[H['reverse_dns']] = ''
    row[H['host']] = c.get('source', '') or ''
    row[H['confidence']] = '0.95'
    row[H['notes']] = f'opencctv_ingest_v2; source={c.get("source", "")}; feed_type={feed_type}; camera_code={c.get("camera_code", "")}'
    row[H['csv_id']] = ''

    rows.append(row)
    added += 1
    next_idx += 1

print(f'Added: {added}, Skipped (dup): {skipped_dup}, No URL: {no_url}')

# Write back
with open(CSV, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(header)
    for r in rows:
        writer.writerow(r)
print(f'New total: {len(rows)}')
