# -*- coding: utf-8 -*-
"""Session 48: CSV coverage of trafficcam locs + Motorola ATIS viewer recon."""
import csv
import json
import os
import re
import subprocess
from collections import Counter
from urllib.parse import urlparse

TEMP = os.environ['TEMP']
ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'


def fetch(url, out=None, timeout=30):
    args = ['curl', '-sL', '-A', UA, '--max-time', str(timeout)]
    if out:
        args += ['-o', os.path.join(TEMP, out)]
    args += ['-w', '%{http_code}|%{content_type}|%{size_download}', url]
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout + 10)
    body = ''
    if out and os.path.exists(os.path.join(TEMP, out)):
        try:
            body = open(os.path.join(TEMP, out), encoding='utf-8', errors='replace').read()
        except OSError:
            pass
    return p.stdout.strip(), body


# --- A. CSV coverage ---
rows = list(csv.DictReader(open(ROOT + r'\controllable_Webcams.csv', newline='', encoding='utf-8')))
tc_rows = []
for r in rows:
    u = (r.get('live_stream_url') or '') + '|' + (r.get('url') or '')
    if 'trafficcam.calgary.ca' in u:
        m = re.findall(r'loc(\d+)\.jpg', u)
        tc_rows.append((r['csv_id'], int(m[0]) if m else None, r['project_name'], r['live_status'],
                        r.get('notes', '')[:60]))
print('CSV trafficcam.calgary.ca rows:', len(tc_rows))
by_loc = {loc: (cid, name, ls, nt) for cid, loc, name, ls, nt in tc_rows if loc is not None}
print('unique loc ids in csv:', len(by_loc))
alive = set(range(0, 224))
missing = sorted(alive - set(by_loc))
extra = sorted(set(by_loc) - alive)
print('alive locs NOT in csv:', len(missing), missing)
print('csv locs outside 0..223:', extra)
print('live_status counts:', Counter(ls for _, _, _, ls, _ in tc_rows))
# junk-name sample (has · · #)
junk = [(cid, loc, name) for cid, loc, name, ls, nt in tc_rows if name and name.count('·') >= 2]
print('junk-named rows (· · pattern):', len(junk), junk[:5])
good = [(cid, loc, name) for cid, loc, name, ls, nt in tc_rows if name and 'webcam' in name.lower() or (name and '/' in name)]
print('good-named rows:', len(good), good[:5])

# --- B. Motorola CMPIC / ATIS viewer ---
print('\n--- Motorola host ---')
for name in ('calgary_cams.html', 'calgary_atis.html'):
    h = open(os.path.join(TEMP, name), encoding='utf-8', errors='replace').read()
    for m in re.finditer(r'motorolasolutions[^"\'\s<>]*', h):
        s = max(0, m.start() - 250)
        e = min(len(h), m.end() + 250)
        print('%s ctx: %s' % (name[:6], re.sub(r'\s+', ' ', h[s:e])[:380]))
        break

print('\n--- cmpic probes ---')
for url in ('https://calgary-cwiprod.motorolasolutions.com/',
            'https://calgary-cwiprod.motorolasolutions.com/cmpic/',
            'https://calgary-cwiprod.motorolasolutions.com/axis-cgi/mjpg/video.cgi',
            'https://calgary-cwiprod.motorolasolutions.com/camera/list',
            'https://calgary-cwiprod.motorolasolutions.com/api/cameras',
            'http://calgary-cwiprod.motorolasolutions.com/'):
    meta, body = fetch(url, timeout=15)
    print(' %-72s -> %s %r' % (url[:72], meta, (body or '')[:90].replace('\n', ' ')))

# --- C. 511 Alberta Cctv coverage ---
ab_rows = [r for r in rows if '511.alberta.ca/map/Cctv' in
           ((r.get('live_stream_url') or '') + (r.get('url') or ''))]
print('\nCSV 511.alberta.ca Cctv rows:', len(ab_rows))
ab_ids = set()
for r in ab_rows:
    m = re.search(r'Cctv/(\d+)', (r.get('live_stream_url') or '') + (r.get('url') or ''))
    if m:
        ab_ids.add(m.group(1))
print('unique AB Cctv ids:', len(ab_ids), 'live_status:', Counter(r['live_status'] for r in ab_rows))
sample = ab_rows[0]
print('sample AB row:', sample['csv_id'], sample['project_name'][:50], (sample['live_stream_url'] or sample['url'])[:80])
