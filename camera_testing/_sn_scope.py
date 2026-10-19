import os
import re
import subprocess
import csv
import time

TEMP = os.environ['TEMP']
ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'

rows = list(csv.DictReader(open(ROOT + r'\controllable_Webcams.csv', newline='', encoding='utf-8')))

print('--- all rows w/ trafficvision_id=feratel-NNNNN ---')
fer_rows = []
for r in rows:
    m = re.search(r'trafficvision_id=feratel:feratel-(\d+)', r.get('notes') or '')
    if not m:
        continue
    try:
        lat = float(r.get('lat') or 'nan')
        lon = float(r.get('lon') or 'nan')
    except ValueError:
        lat = lon = float('nan')
    in_es = 35.0 <= lat <= 44.5 and -10.5 <= lon <= 4.5
    fer_rows.append((m.group(1), r, in_es))
print(' total feratel rows:', len(fer_rows))
sp = [(cid, r) for cid, r, es in fer_rows if es]
print(' in Spain bbox:', len(sp))
for cid, r in sp:
    print('  %s %s | %s | %s | %s,%s | %s' % (
        cid, r['csv_id'], (r['project_name'] or '')[:44], r['live_status'],
        r['lat'], r['lon'], (r.get('city') or '-')))

print('\n--- hotspot freshness: ETag/size twice for 15110 ---')
def get_meta(url, out):
    p = subprocess.run(['curl', '-sL', '-A', UA, '--max-time', '30', '-D', '-',
                        '-o', os.path.join(TEMP, out), '-w', '|%{size_download}', url],
                       capture_output=True, timeout=40)
    raw = p.stdout.decode('latin-1', 'replace')
    hdr = raw.split('\n')
    et = [x for x in hdr if x.lower().startswith('etag')]
    lm = [x for x in hdr if x.lower().startswith('last-modified')]
    sz = raw.rsplit('|', 1)[-1]
    return (et[0].strip() if et else '-', lm[0].strip() if lm else '-', sz)

m1 = get_meta('https://webtvhotspot.feratel.com/hotspot/37/15110/0.jpeg?design=v3', 'hs1.jpg')
print(' t0:', m1)
time.sleep(45)
m2 = get_meta('https://webtvhotspot.feratel.com/hotspot/37/15110/0.jpeg?design=v3', 'hs2.jpg')
print(' t45:', m2)
print(' changed:', m1[2] != m2[2])
