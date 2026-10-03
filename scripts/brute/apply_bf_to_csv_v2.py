"""Add RTSP live URLs to CSV for unlocked cams.

Reads RTSP BF results, finds RTSP endpoints with valid creds, and adds them
as live_stream_url entries for the matching IP cams.
"""
import csv
import os
import time
import random
import json
import re

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
RTSP_BF = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\rtsp_bf.json'
BF_PROG = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\bf_progress.json'

print('Loading RTSP BF results...', flush=True)
with open(RTSP_BF) as f:
    rtsp_bf = json.load(f)

# Build unlocked cams map by IP
unlocked = {}
for k, v in rtsp_bf.items():
    if isinstance(v, dict) and v.get('unlocked'):
        ip = v.get('ip')
        port = v.get('port', 554)
        found = v.get('found', [])
        if ip and found:
            f0 = found[0]
            creds = f0.get('creds', ['', ''])
            user, pwd = creds[0], creds[1]
            path = f0.get('path', '/')
            # Build RTSP URL with auth
            if user:
                rtsp_url = f'rtsp://{user}:{pwd}@{ip}:{port}{path}'
            else:
                rtsp_url = f'rtsp://{ip}:{port}{path}'
            unlocked[ip] = {
                'user': user,
                'pass': pwd,
                'path': path,
                'protocol': f0.get('protocol'),
                'rtsp_url': rtsp_url,
            }

print(f'  {len(unlocked):,} unlocked RTSP cams', flush=True)

# Also add HTTP BF unlocks - find RTSP endpoints for these IPs
http_unlocked = {}
with open(BF_PROG) as f:
    bf_prog = json.load(f)
for k, v in bf_prog.items():
    if isinstance(v, dict) and v.get('unlocked'):
        creds = v.get('creds', '').split(':')
        if len(creds) >= 2:
            user, pwd = creds[0], creds[1]
            url = k.replace('http://', '').replace('https://', '')
            parts = url.split(':')
            if len(parts) >= 2:
                ip = parts[0]
                if ip not in unlocked:
                    http_unlocked[ip] = {
                        'user': user,
                        'pass': pwd,
                        'protocol': 'http',
                    }

print(f'  HTTP unlocked: {len(http_unlocked):,}', flush=True)

# Try RTSP on port 554 for HTTP-unlocked IPs - SKIP (too slow)
print('\nSkipping RTSP probing on port 554 for HTTP-unlocked IPs (too slow)', flush=True)
new_rtsp = 0

# Merge http_unlocked into unlocked so they get applied
for ip, info in http_unlocked.items():
    if ip not in unlocked:
        unlocked[ip] = info

print(f'  New RTSP: {new_rtsp}', flush=True)
print(f'  Total unlocked with RTSP: {len(unlocked):,}', flush=True)

# Save updated RTSP BF
with open(RTSP_BF, 'w') as f:
    json.dump(rtsp_bf, f, indent=2)

print('\nLoading CSV...', flush=True)
csv.field_size_limit(2**31-1)
with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    header = reader.fieldnames
print(f'  {len(rows):,} rows', flush=True)

# Find rows by IP
n_updated = 0
for i, row in enumerate(rows):
    url = row.get('url', '') or ''
    lsurl = row.get('live_stream_url', '') or ''
    matched_ip = None
    for u in [url, lsurl]:
        m = re.match(r'(?:rtsp|http)s?://(?:[^@]+@)?(\d+\.\d+\.\d+\.\d+)', u)
        if m:
            matched_ip = m.group(1)
            break
    if matched_ip and matched_ip in unlocked:
        u_info = unlocked[matched_ip]
        if u_info.get('protocol') == 'rtsp':
            rows[i]['live_stream_url'] = u_info['rtsp_url']
            rows[i]['auth_user'] = u_info['user']
            rows[i]['auth_pass'] = u_info['pass']
            notes = rows[i].get('notes') or ''
            rows[i]['notes'] = notes + f'; RTSP_BF_unlocked={u_info["user"]}:{u_info["pass"]}'
            n_updated += 1
        elif u_info.get('protocol') == 'http' and not rows[i].get('auth_user'):
            rows[i]['auth_user'] = u_info['user']
            rows[i]['auth_pass'] = u_info['pass']
            notes = rows[i].get('notes') or ''
            rows[i]['notes'] = notes + f'; HTTP_BF_unlocked={u_info["user"]}:{u_info["pass"]}'
            n_updated += 1

print(f'\n  Updated {n_updated:,} rows', flush=True)

if n_updated > 0:
    tmp = CSV_PATH + '.tmp'
    # Clean up rows that have None fields not in header
    extra_fields = set()
    for row in rows:
        for k in row.keys():
            if k not in header:
                extra_fields.add(k)
    if extra_fields:
        print(f'  Removing extra fields: {extra_fields}', flush=True)
        for row in rows:
            for k in extra_fields:
                row.pop(k, None)
    for attempt in range(60):
        try:
            with open(tmp, 'w', encoding='utf-8', newline='') as f:
                w = csv.DictWriter(f, fieldnames=header, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
                w.writeheader()
                w.writerows(rows)
            os.replace(tmp, CSV_PATH)
            print(f'  Saved CSV with {n_updated:,} updates', flush=True)
            break
        except PermissionError:
            time.sleep(2 + random.uniform(0, 3))
