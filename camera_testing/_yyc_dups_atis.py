# -*- coding: utf-8 -*-
"""Session 48: dup-url analysis + ATIS iframe + aggregator cam names."""
import csv
import json
import os
import re
from collections import Counter, defaultdict

TEMP = os.environ['TEMP']
ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'

# 1) ATIS iframe / embed
for name in ('calgary_atis.html', 'calgary_cams.html'):
    h = open(os.path.join(TEMP, name), encoding='utf-8', errors='replace').read()
    print('=====', name)
    for pat in (r'<iframe[^>]+src=["\']([^"\']+)', r'data-src=["\']([^"\']+)',
                r'cwiprod[^"\'\s<>]*', r'cmpic[^"\'\s<>]*', r'atis[^"\'\s<>]*'):
        m = sorted(set(re.findall(pat, h, re.I)))
        if m:
            print(' %s ->' % pat[:22], [x[:130] for x in m[:8]])

# 2) dup analysis of trafficcam rows
rows = list(csv.DictReader(open(ROOT + r'\controllable_Webcams.csv', newline='', encoding='utf-8')))
tc = [r for r in rows if 'trafficcam.calgary.ca' in
      ((r.get('live_stream_url') or '') + (r.get('url') or ''))]
print('\ntrafficcam rows:', len(tc))
url_forms = Counter()
by_loc_forms = defaultdict(list)
for r in tc:
    u1 = r.get('url') or ''
    u2 = r.get('live_stream_url') or ''
    m = re.search(r'loc(\d+)\.jpg', u1 + u2)
    loc = int(m.group(1)) if m else -1
    url_forms[(u1, u2)] += 1
    by_loc_forms[loc].append((r['csv_id'], u1, u2, r['project_name'][:40]))
print('unique (url,live_stream_url) pairs:', len(url_forms))
dups = [loc for loc, lst in by_loc_forms.items() if len(lst) > 1]
print('locs with multiple rows:', len(dups))
for loc in dups[:6]:
    print(' loc', loc)
    for e in by_loc_forms[loc]:
        print('   ', e)

# 3) trafficcam rows: do good rows have coords?
sample_good = next(r for r in tc if 'disc_173' in r['csv_id'])
print('\ngood row sample:', sample_good['csv_id'], sample_good['project_name'])
print(' lat/lon/geo:', sample_good['lat'], sample_good['lon'], sample_good['geo_source'], '| region:', sample_good['region'])
junk = next(r for r in tc if r['project_name'].count('·') >= 2)
print('junk row sample:', junk['csv_id'], junk['project_name'])
print(' lat/lon/geo:', junk['lat'], junk['lon'], junk['geo_source'], '| region:', junk['region'])

# 4) aggregator html: any loc names for missing 159,169,210,223?
h2 = open(os.path.join(TEMP, 'tcagary.html'), encoding='utf-8', errors='replace').read()
print('\ntcagary.html len:', len(h2))
for pat in (r'loc(\d+)', r'511\.alberta[^"\'\s<>]*', r'\.js[^"\'\s]*', r'api[^"\'\s]{0,50}',
            r'camera[^"\'\s]{0,40}'):
    m = sorted(set(re.findall(pat, h2, re.I)))
    if m:
        print(' %s ->' % pat[:22], [x[:100] for x in m[:14]])
