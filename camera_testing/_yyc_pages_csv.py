# -*- coding: utf-8 -*-
"""Session 48: parse calgary.ca + ATIS pages; CSV overlap."""
import csv
import os
import re
from collections import Counter
from urllib.parse import urlparse

TEMP = os.environ['TEMP']
ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'

for name in ('calgary_cams.html', 'calgary_atis.html'):
    p = os.path.join(TEMP, name)
    h = open(p, encoding='utf-8', errors='replace').read()
    print('=====', name, 'len', len(h))
    locs = sorted(set(int(m) for m in re.findall(r'loc(\d+)\.jpg', h)))
    print(' loc ids referenced:', len(locs), locs[:30], '...' if len(locs) > 30 else '')
    hosts = Counter(urlparse(u).netloc for u in re.findall(r'https?://[^"\'\s<>]+', h))
    print(' top hosts:', [x for x in hosts.most_common(12)
                          if not any(d in x[0] for d in ('google', 'gstatic', 'calgary.ca'))][:8])
    # any other image/cam urls
    imgs = sorted(set(u for u in re.findall(r'https?://[^"\'\s<>]+\.(?:jpg|png|m3u8|mjpg)[^"\'\s<>]*', h, re.I)
                      if 'trafficcam' in u or 'camera' in u.lower()))
    print(' cam-ish urls:', [u[:100] for u in imgs[:8]])
    # headings that look like road groups
    roads = re.findall(r'<h[23][^>]*>([^<]{3,60})</h[23]>', h)
    print(' headings:', roads[:24])

# csv overlap
rows = list(csv.DictReader(open(ROOT + r'\controllable_Webcams.csv', newline='', encoding='utf-8')))
for needle in ('trafficcam.calgary', 'calgary', 'yyc', 'deerfoot', 'stoney trail'):
    hits = [r for r in rows if needle.lower() in ' '.join(
        (r.get(k) or '') for k in ('url', 'live_stream_url', 'notes', 'project_name',
                                   'description', 'city', 'host')).lower()]
    print('CSV %-20s -> %d' % (needle, len(hits)))
    for r in hits[:6]:
        print('   %s | %s | %s' % (r['csv_id'], (r['project_name'] or '')[:40],
                                   (r['live_stream_url'] or r['url'] or '')[:70]))
# prefix check
pref = Counter(r['csv_id'].split('_')[0] for r in rows if r.get('csv_id'))
for p in ('yyc', 'cal', 'cgy'):
    print('prefix %s: %d' % (p, pref.get(p, 0)))
