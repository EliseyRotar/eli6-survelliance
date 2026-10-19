import os
import re
import subprocess
import csv

TEMP = os.environ['TEMP']
ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'


def curl(args, timeout=30):
    p = subprocess.run(['curl', '-s', '-A', UA, '--max-time', str(timeout)] + args,
                       capture_output=True, text=True, timeout=timeout + 10)
    return p.stdout


print('--- 403 body plain ---')
print(repr(curl(['https://media.trafficvision.live/feratel/15110.mp4']))[:300])
print('--- 403 w/ referer ---')
print(repr(curl(['-e', 'https://trafficvision.live/', 'https://media.trafficvision.live/feratel/15110.mp4']))[:300])
print('--- 403 w/ referer trafficvision.live root + range ---')
print(repr(curl(['-e', 'https://app.trafficvision.live/', '-r', '0-100',
                 'https://media.trafficvision.live/feratel/15111.mp4']))[:300])

print('\n--- existing Sierra Nevada rows state ---')
rows = list(csv.DictReader(open(ROOT + r'\controllable_Webcams.csv', newline='', encoding='utf-8')))
for r in rows:
    if 'feratel/1511' in (r.get('url') or ''):
        print(' ', r['csv_id'], {k: (r.get(k) or '')[:60] for k in
                                 ('project_name', 'type', 'live_status', 'http_status',
                                  'region', 'city', 'geo_source', 'notes')})

print('\n--- other feratel mp4 rows (sample of live_status) ---')
fer = [r for r in rows if 'media.trafficvision.live/feratel/' in (r.get('url') or '')]
from collections import Counter
print(' count', len(fer), Counter(r['live_status'] for r in fer))

print('\n--- hotspot freshness (Last-Modified / Age) ---')
for cid in (15110, 15112, 15111):
    print('  %d:' % cid, curl(['-sIL', 'https://webtvhotspot.feratel.com/hotspot/37/%d/0.jpeg?design=v3' % cid])
          .replace('\r', ' | ').split(' | ')[-8:])
print('--- pradollano snapshot headers ---')
print(curl(['-sIL', 'https://recursos.sierranevada.es/_extras/fotos_camaras/pradollano/snap_c1.jpg'])
      .replace('\r', ' | ').split(' | ')[-10:])

print('\n--- CSV pradollano / laguna / veleta ---')
for needle in ('pradollano/snap', 'Zona Laguna', 'Zona Veleta', 'Mirlo Blanco', 'Montebajo', 'Borreguiles'):
    hits = [r for r in rows if needle.lower() in ' '.join(
        (r.get(k) or '') for k in ('url', 'live_stream_url', 'notes', 'project_name', 'description')).lower()]
    print(' %-16s -> %d %s' % (needle, len(hits), [(h['csv_id'], h['project_name'][:24]) for h in hits[:3]]))

print('\n--- heading vs cam positions (es page) ---')
html = open(TEMP + r'\sn_webcams.html', encoding='utf-8', errors='replace').read()
heads = ['Pradollano', 'Borreguiles', 'La Visera', 'Jardín Alpino', 'Granados', 'Rebeco']
hp = [(html.find(h), h) for h in heads]
cp = [(m.start(), m.group(1)) for m in re.finditer(r'cam=(15\d{3})', html)]
print(' headings pos:', hp)
print(' cam pos:', cp[:20])
