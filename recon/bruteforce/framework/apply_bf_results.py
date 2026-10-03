"""apply_bf_results.py — Apply cached brute-force results back to CSV.

For each cached hit:
- Find matching row by host + port
- Update auth_user, auth_pass, auth_required, notes

Uses O_EXCL lock file for cross-process safety.
"""
import csv
import json
import os
import re
import sys
import time

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
CACHE_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\backups\cam_bruteforce_results.json'
LOCK_PATH = CSV_PATH + '.lock'


def main():
    with open(CACHE_PATH, 'r') as f:
        cache = json.load(f)
    print(f'cached entries: {len(cache)}')

    # Acquire lock
    lock_fd = None
    for attempt in range(120):
        try:
            lock_fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            break
        except FileExistsError:
            time.sleep(0.5 + 0.5 * (attempt % 10))
    if lock_fd is None:
        # Force-clear stale lock
        try:
            age = time.time() - os.stat(LOCK_PATH).st_mtime
            if age > 60:
                os.remove(LOCK_PATH)
                lock_fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_RDWR)
        except Exception:
            pass
        if lock_fd is None:
            print('could not acquire lock')
            return
    print('lock acquired')

    try:
        with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
            rows = list(csv.reader(f))
        header = rows[0]
        cols = {h: i for i, h in enumerate(header)}
        HOST = cols['host']
        URL = cols['url']
        AUTH_USER = cols.get('auth_user', None)
        AUTH_PASS = cols.get('auth_pass', None)
        AUTH_REQ = cols.get('auth_required', None)
        NOTES = cols.get('notes', None)

        updated = 0
        for r in rows[1:]:
            if len(r) <= HOST:
                continue
            host = r[HOST].strip()
            url = r[URL] if len(r) > URL else ''
            m = re.match(r'https?://[^:/]+:(\d+)', url)
            port = int(m.group(1)) if m else 80
            cache_key = f'{host}:{port}'
            if cache_key not in cache:
                continue
            result = cache[cache_key]
            creds_set = False
            new_note_bits = []
            if result.get('http_creds'):
                for cp in result['http_creds']:
                    if ':' in cp:
                        user, pwd = cp.split(':', 1)
                        if AUTH_USER is not None and AUTH_PASS is not None:
                            r[AUTH_USER] = user
                            r[AUTH_PASS] = pwd
                            creds_set = True
                            new_note_bits.append(f'http_creds={cp}')
                        break
            if result.get('cves'):
                for cve in result['cves']:
                    new_note_bits.append(f'cve={cve}')
                    creds_set = True
            if result.get('rtsp_unauth'):
                for path in result['rtsp_unauth']:
                    new_note_bits.append(f'rtsp_unauth={path}')
            if result.get('rtsp_creds'):
                for cp in result['rtsp_creds']:
                    new_note_bits.append(f'rtsp_creds={cp}')
            if creds_set and AUTH_REQ is not None:
                r[AUTH_REQ] = 'yes'
            if new_note_bits and NOTES is not None:
                existing = r[NOTES] if len(r) > NOTES else ''
                new = ' | '.join(new_note_bits)[:200]
                r[NOTES] = (existing + ' | bf:' + new)[:500] if existing else ('bf:' + new)[:500]
            if new_note_bits:
                updated += 1

        print(f'updated {updated} rows')

        # Atomic write with retries
        tmp = CSV_PATH + '.tmp'
        for wa in range(15):
            try:
                with open(tmp, 'w', encoding='utf-8', newline='') as f:
                    w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
                    for r in rows:
                        w.writerow(r)
                os.replace(tmp, CSV_PATH)
                break
            except PermissionError:
                time.sleep(0.5 + 0.3 * wa)
        print('done')
    finally:
        try:
            os.close(lock_fd)
        except Exception:
            pass
        try:
            os.remove(LOCK_PATH)
        except OSError:
            pass


if __name__ == '__main__':
    main()
