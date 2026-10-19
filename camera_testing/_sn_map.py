import os
import re
import csv

TEMP = os.environ['TEMP']
ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
html = open(TEMP + r'\sn_webcams.html', encoding='utf-8', errors='replace').read()

# map each cam-ish url to nearest preceding heading
print('--- embeds in page order w/ context ---')
for m in re.finditer(r'https?://[^"\'\s\\]*(?:webtv|camaras|cam)[^"\'\s\\]*', html):
    start = m.start()
    ctx = html[max(0, start - 3000):start]
    heads = re.findall(r'<h[1-4][^>]*>(.*?)</h[1-4]>', ctx, re.S)
    head = re.sub(r'<[^>]+>', '', heads[-1]).strip() if heads else '?'
    print('  %-70s <= %s' % (m.group(0)[:70], head[:70]))

print()
print('--- CSV overlap ---')
rows = list(csv.DictReader(open(ROOT + r'\controllable_Webcams.csv', newline='', encoding='utf-8')))
for needle in ['cam=15110', 'cam=15111', 'cam=15112', 'cam=15113', 'cam=15114',
               'feratel', 'sierranevada', 'sierra nevada', 'Sierra Nevada',
               'webtv.feratel', 'camaras/313', 'recursos.sierranevada']:
    hits = [r for r in rows if needle in ' '.join(
        (r.get(k) or '') for k in ('url', 'live_stream_url', 'notes', 'project_name',
                                   'description', 'org', 'host'))]
    print('  %-24s -> %d' % (needle, len(hits)), [(h['csv_id'], h['project_name'][:30]) for h in hits[:4]])
