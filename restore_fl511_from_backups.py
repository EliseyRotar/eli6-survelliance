"""Restore FL511 cams from all backups.

Scans each backup for rows with 'dis-se' in live_stream_url (FL511 m3u8 format),
deduplicates, and appends missing rows to current CSV.
"""
import csv
import json
import os
import re
import time
import random
from collections import OrderedDict

WORK_DIR = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
BACKUP_DIR = os.path.join(WORK_DIR, 'backups')
CSV_PATH = os.path.join(WORK_DIR, 'controllable_Webcams.csv')


def main():
    print('Loading current CSV...', flush=True)
    csv.field_size_limit(2**31-1)
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        reader = csv.DictReader(f)
        cur_rows = list(reader)
        header = reader.fieldnames
    cur_urls = set()
    cur_live_urls = set()
    for row in cur_rows:
        cur_urls.add((row.get('url') or '').strip().lower())
        cur_live_urls.add((row.get('live_stream_url') or '').strip().lower())

    # Backup dirs to scan (latest first, then older)
    backups = []
    for name in os.listdir(BACKUP_DIR):
        path = os.path.join(BACKUP_DIR, name, 'controllable_Webcams.csv')
        if os.path.exists(path):
            mtime = os.path.getmtime(path)
            backups.append((mtime, path, name))
    backups.sort(reverse=True)
    print(f'Found {len(backups)} backups to scan', flush=True)

    # Collect fl511-style rows from all backups
    fl511_rows = OrderedDict()  # url -> row dict
    fl511_pattern = re.compile(r'dis-se\d+\.divas\.cloud:8200', re.I)

    for mtime, path, name in backups:
        try:
            with open(path, 'r', encoding='utf-8', errors='replace', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ls = (row.get('live_stream_url') or '').lower()
                    url = (row.get('url') or '').lower()
                    if fl511_pattern.search(ls) or fl511_pattern.search(url):
                        # Use live_stream_url as unique key
                        key = (row.get('live_stream_url') or '').strip().lower()
                        if key and key not in fl511_rows:
                            fl511_rows[key] = row
        except Exception as e:
            print(f'  Error reading {name}: {e}', flush=True)

    print(f'Found {len(fl511_rows):,} unique FL511 rows across all backups', flush=True)

    # Filter to those not in current CSV
    to_add = []
    for key, row in fl511_rows.items():
        # Check if already in current CSV by url or live_stream_url
        url_lower = (row.get('url') or '').strip().lower()
        ls_lower = (row.get('live_stream_url') or '').strip().lower()
        if url_lower in cur_urls or ls_lower in cur_live_urls:
            continue
        # Strip the auth_user/auth_pass fields — token may have expired.
        # HLS proxy will auto-refresh.
        if 'auth_user' in row:
            row['auth_user'] = ''
        if 'auth_pass' in row:
            row['auth_pass'] = ''
        # Mark live_status as 'live' (proxy will handle)
        if row.get('live_status') in ('dead', 'auth_required', ''):
            row['live_status'] = 'live'
        to_add.append(row)

    print(f'{len(to_add):,} FL511 rows to add (not in current CSV)', flush=True)

    if not to_add:
        print('Nothing to add', flush=True)
        return

    # Re-number idx
    max_idx = 0
    for row in cur_rows:
        try:
            idx = int(row.get('idx', 0))
            max_idx = max(max_idx, idx)
        except Exception:
            pass

    # Append
    new_rows = []
    for row in to_add:
        max_idx += 1
        row['idx'] = str(max_idx)
        if not row.get('csv_id'):
            row['csv_id'] = f'fl511_restored_{max_idx:04d}'
        new_rows.append(row)

    print(f'Re-numbered {len(new_rows):,} rows, will append to CSV', flush=True)

    # Save with retry
    tmp = CSV_PATH + '.tmp'
    chunk_size = 10000
    total = len(cur_rows) + len(new_rows)
    print(f'Writing {total:,} rows...', flush=True)
    for attempt in range(20):
        try:
            with open(tmp, 'w', encoding='utf-8', newline='') as f:
                w = csv.DictWriter(f, fieldnames=header, lineterminator='\n',
                                   quoting=csv.QUOTE_MINIMAL, extrasaction='ignore')
                w.writeheader()
                for i in range(0, len(cur_rows), chunk_size):
                    w.writerows(cur_rows[i:i+chunk_size])
                for i in range(0, len(new_rows), chunk_size):
                    w.writerows(new_rows[i:i+chunk_size])
            os.replace(tmp, CSV_PATH)
            print(f'Saved CSV with {len(new_rows):,} restored FL511 rows', flush=True)
            print(f'CSV now has {total:,} rows', flush=True)
            return
        except PermissionError as e:
            if attempt % 5 == 0:
                print(f'  retry {attempt}: {e}', flush=True)
            time.sleep(2 + random.uniform(0, 3))

    print('ERROR: failed to save after 20 retries', flush=True)


if __name__ == '__main__':
    import csv  # at top-level too for safety
    main()
