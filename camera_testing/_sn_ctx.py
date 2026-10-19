import os
import re
import csv

TEMP = os.environ['TEMP']
ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
html = open(TEMP + r'\sn_webcams.html', encoding='utf-8', errors='replace').read()

print('--- context around cam=NNNNN (250 chars before / 120 after) ---')
for m in re.finditer(r'cam=(\d{5})', html):
    s = max(0, m.start() - 250)
    ctx = re.sub(r'\s+', ' ', html[s:m.start() + 130])
    print('  [%s] …%s' % (m.group(1), ctx[-330:]))

print()
print('--- CSV rows ---')
rows = list(csv.DictReader(open(ROOT + r'\controllable_Webcams.csv', newline='', encoding='utf-8')))
for cid in ('tv_129262', 'tv_129264', 'tv_129816'):
    for r in rows:
        if r['csv_id'] == cid:
            print(' ', cid, {k: (r.get(k) or '')[:70] for k in
                             ('project_name', 'city', 'region', 'lat', 'lon',
                              'url', 'live_stream_url', 'notes')})
print('etraffic rows:', sum(1 for r in rows if 'etraffic' in ((r.get('url') or '') + (r.get('notes') or ''))))
dgt313 = [r for r in rows if re.search(r'cameras?/313\.jpg|/313\.jpg', (r.get('url') or '') + (r.get('live_stream_url') or ''))]
print('313.jpg rows:', [(r['csv_id'], r['project_name']) for r in dgt313])
