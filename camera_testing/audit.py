"""Comprehensive audit of all camera systems.

Checks:
1. CSV integrity (row counts, columns, no empty rows, no malformed rows)
2. SQLite DB matches CSV
3. Duplicate URLs
4. Field fill rates
5. Source distribution
6. Streaming video format distribution
"""
import csv
import os
import sys
import sqlite3
import re
from collections import Counter

sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
DB_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\webcams.db'

csv.field_size_limit(2**31 - 1)


def print_section(title):
    print()
    print('=' * 70)
    print(f'  {title}')
    print('=' * 70)


def main():
    print_section('FILE SIZE CHECK')
    csv_size = os.path.getsize(CSV_PATH)
    db_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
    print(f'CSV size: {csv_size:,} bytes ({csv_size/1024/1024:.1f} MB)')
    print(f'DB size:  {db_size:,} bytes ({db_size/1024/1024:.1f} MB)')

    print_section('CSV INTEGRITY')
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        rows = list(csv.reader(f))
    header = rows[0]
    print(f'Total rows: {len(rows):,}')
    print(f'Header cols: {len(header)}')
    print(f'Header: {header[:8]}...{header[-3:]}')

    # Column distribution
    col_counts = Counter()
    bad_rows = []
    empty_rows = []
    for i, r in enumerate(rows):
        col_counts[len(r)] += 1
        if len(r) != 35:
            bad_rows.append((i, len(r)))
    for i, r in enumerate(rows[1:], 1):
        if not r or len(r) < 5 or not r[0] or not r[1] or not r[3]:
            empty_rows.append((i, len(r) if r else 0))
    print(f'\nRow column distribution:')
    for c, n in sorted(col_counts.items()):
        print(f'  {c} cols: {n:,} rows')
    print(f'\nBad rows (col count != 35): {len(bad_rows)}')
    if bad_rows:
        for i, c in bad_rows[:5]:
            print(f'  row {i}: {c} cols')
    print(f'Empty rows: {len(empty_rows)}')

    print_section('FIELD FILL RATES')
    if len(rows) > 1:
        total = len(rows) - 1
        for ci, h in enumerate(header):
            filled = sum(1 for r in rows[1:] if len(r) > ci and r[ci])
            rate = filled / total * 100
            print(f'  [{ci:2d}] {h:<22} {filled:>7,} / {total:,}  ({rate:5.1f}%)')

    print_section('SOURCE DISTRIBUTION')
    sources = Counter()
    if len(rows) > 1:
        for r in rows[1:]:
            if len(r) > 33 and r[33]:
                for m in re.finditer(r'(\w+)_id=', r[33]):
                    sources[m.group(1)] += 1
    for src, n in sources.most_common(20):
        print(f'  {src:<30} {n:>7,}')

    print_section('VIDEO FORMAT DISTRIBUTION')
    formats = Counter()
    if len(rows) > 1:
        for r in rows[1:]:
            if len(r) > 3:
                url = r[3].lower()
                if '.m3u8' in url:
                    formats['HLS .m3u8'] += 1
                elif '.mp4' in url:
                    formats['MP4'] += 1
                elif 'mjpeg' in url or 'mjpg' in url:
                    formats['MJPEG'] += 1
                elif 'youtube' in url or 'ipcamlive' in url:
                    formats['YouTube/IPCamLive'] += 1
                elif '.jpg' in url or '.jpeg' in url:
                    formats['JPEG'] += 1
                elif 'rtsp://' in url:
                    formats['RTSP'] += 1
                elif not url:
                    formats['[empty]'] += 1
                else:
                    formats['other'] += 1
    for fmt, n in formats.most_common():
        print(f'  {fmt:<25} {n:>7,}')

    print_section('DUPLICATE URL CHECK')
    seen = {}
    dupes = 0
    for i, r in enumerate(rows[1:], 1):
        if len(r) > 3 and r[3]:
            url = r[3].lower().strip()
            if url in seen:
                dupes += 1
            else:
                seen[url] = i
    print(f'Duplicate live_stream_urls: {dupes:,}')
    print(f'Unique live URLs: {len(seen):,}')

    print_section('PRIVATE VS PUBLIC')
    private = 0
    public = 0
    other = 0
    for r in rows[1:]:
        if len(r) > 15:
            cat = r[15].lower()
            if cat == 'private':
                private += 1
            elif cat == 'public':
                public += 1
            else:
                other += 1
    print(f'Private/Residential cams: {private:,}')
    print(f'Public cams: {public:,}')
    print(f'Other: {other:,}')

    print_section('AUTHENTICATION REQUIREMENTS')
    auth_required = 0
    auth_user_set = 0
    for r in rows[1:]:
        if len(r) > 5:
            if r[5].lower() == 'true':
                auth_required += 1
            if len(r) > 6 and r[6]:
                auth_user_set += 1
    print(f'Cams requiring auth: {auth_required:,}')
    print(f'Cams with known auth credentials: {auth_user_set:,}')

    print_section('GEOGRAPHIC COVERAGE')
    countries = Counter()
    cities = Counter()
    for r in rows[1:]:
        if len(r) > 21:
            if r[19]: countries[r[19]] += 1
            if r[21]: cities[r[21]] += 1
    print(f'Unique countries: {len(countries):,}')
    print(f'Unique cities: {len(cities):,}')
    print(f'Top 15 countries:')
    for c, n in countries.most_common(15):
        cs = c.encode('ascii', 'replace').decode() if c else 'NULL'
        print(f'  {cs:<30} {n:>7,}')

    print_section('SQLITE DB CHECK')
    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        db_count = cur.execute('SELECT COUNT(*) FROM webcams').fetchone()[0]
        print(f'SQLite row count: {db_count:,}')
        print(f'CSV row count (excl header): {len(rows)-1:,}')
        if db_count == len(rows) - 1:
            print('  MATCH OK')
        else:
            print(f'  MISMATCH: diff = {db_count - (len(rows)-1):,}')
        # Index check
        for idx in cur.execute("SELECT name, sql FROM sqlite_master WHERE type='index'"):
            print(f'  index: {idx[0]}')
        conn.close()
    else:
        print(f'DB not found: {DB_PATH}')

    print()
    print('=' * 70)
    print('  AUDIT COMPLETE')
    print('=' * 70)


if __name__ == '__main__':
    main()
