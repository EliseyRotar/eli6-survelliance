"""Apply RTSP BF unlocks to CSV - add auth_user/auth_pass to RTSP rows."""
import csv
import os
import time
import random
import json

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
RTSP_BF = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\rtsp_bf.json'
BF_PROG = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\bf_progress.json'

print('Loading RTSP BF results...', flush=True)
with open(RTSP_BF) as f:
    rtsp_bf = json.load(f)
with open(BF_PROG) as f:
    bf_prog = json.load(f)

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
            unlocked[(ip, port)] = {
                'user': creds[0],
                'pass': creds[1],
                'path': f0.get('path'),
                'protocol': f0.get('protocol'),
            }

print(f'  {len(unlocked):,} unlocked RTSP cams', flush=True)

# Also add HTTP BF unlocks
for k, v in bf_prog.items():
    if isinstance(v, dict) and v.get('unlocked'):
        creds = v.get('creds', '').split(':')
        if len(creds) >= 2:
            user, pwd = creds[0], creds[1]
            # URL like http://IP:PORT/path -> IP, PORT
            url = k.replace('http://', '').replace('https://', '')
            parts = url.split(':')
            if len(parts) >= 2:
                ip = parts[0]
                port = parts[1].split('/')[0]
                try:
                    port = int(port)
                    unlocked[(ip, port)] = {
                        'user': user,
                        'pass': pwd,
                        'path': '/' + '/'.join(parts[1].split('/')[1:]) if '/' in parts[1] else '/',
                        'protocol': 'http',
                    }
                except:
                    pass

print(f'  Total unlocked: {len(unlocked):,}', flush=True)

print('\nLoading CSV...', flush=True)
csv.field_size_limit(2**31-1)
with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    header = reader.fieldnames
print(f'  {len(rows):,} rows', flush=True)

# Find RTSP rows by IP:port
import re
n_updated = 0
for i, row in enumerate(rows):
    url = row.get('url', '') or ''
    lsurl = row.get('live_stream_url', '') or ''
    for u in [url, lsurl]:
        if u.startswith('rtsp://'):
            m = re.match(r'rtsp://(?:[^@]+@)?(\d+\.\d+\.\d+\.\d+):?(\d+)?(/.*)?', u)
            if m:
                ip = m.group(1)
                port = int(m.group(2)) if m.group(2) else 554
                if (ip, port) in unlocked:
                    u_info = unlocked[(ip, port)]
                    rows[i]['auth_user'] = u_info['user']
                    rows[i]['auth_pass'] = u_info['pass']
                    rows[i]['notes'] = (rows[i].get('notes') or '') + f'; BF unlocked={u_info["user"]}:{u_info["pass"]}'
                    n_updated += 1
                    break

print(f'\n  Updated {n_updated:,} RTSP rows', flush=True)

# Save with retry
if n_updated > 0:
    tmp = CSV_PATH + '.tmp'
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
