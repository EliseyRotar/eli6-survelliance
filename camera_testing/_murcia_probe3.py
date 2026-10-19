import os
import re
import csv
from collections import Counter

TEMP = os.environ['TEMP']
ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'

print('--- wmcam/xmcam page titles & text ---')
for name in ('wmcam', 'xmcam'):
    h = open(os.path.join(TEMP, '%s.html' % name), encoding='utf-8', errors='replace').read()
    t = re.findall(r'<title>([^<]+)</title>', h)
    h1 = re.findall(r'<h\d[^>]*>([^<]+)</h\d>', h)
    txt = re.sub(r'<[^>]+>', ' ', h)
    txt = re.sub(r'\s+', ' ', txt).strip()[:300]
    print(' %s: title=%s h=%s' % (name, t, h1[:3]))
    print('   text:', txt[:220])

print('\n--- meteomurcia station coords in page ---')
mmu = open(os.path.join(TEMP, 'mmu.html'), encoding='utf-8', errors='replace').read()
for pat in (r'[Ll]atitud[^0-9-]{0,10}([\d.,\s-]+)', r'[Ll]ongitud[^0-9-]{0,10}([\d.,\s-]+)',
            r'"lat"\s*:\s*([\d.-]+)', r'"lon"\s*:\s*([\d.-]+)',
            r'Latitud[^<]{0,40}', r'37\.\d{3,}', r'-1\.\d{3,}'):
    m = re.findall(pat, mmu)
    if m:
        print(' %s -> %s' % (pat[:24], m[:6]))

print('\n--- existing camsecure-family row sample ---')
rows = list(csv.DictReader(open(ROOT + r'\controllable_Webcams.csv', newline='', encoding='utf-8')))
cs = [r for r in rows if 'camsecure' in ((r.get('url') or '') + (r.get('live_stream_url') or '')).lower()]
print(' camsecure url rows:', len(cs))
for r in cs[:3]:
    print({k: (r.get(k) or '')[:70] for k in ('csv_id', 'project_name', 'url', 'live_stream_url',
                                              'type', 'category', 'org', 'host', 'live_status')})
hls = [r for r in rows if '.m3u8' in (r.get('live_stream_url') or '') and r['country'] == 'Spain'][:2]
print('\n ES HLS rows sample:')
for r in hls:
    print({k: (r.get(k) or '')[:70] for k in ('csv_id', 'project_name', 'type', 'live_stream_url',
                                              'org', 'host', 'category')})
print(' mmu prefix rows:', sum(1 for r in rows if r['csv_id'].startswith('mmu_')))
