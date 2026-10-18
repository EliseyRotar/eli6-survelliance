import os
import re
import subprocess

html = open(os.environ['TEMP'] + r'\crtvg_cams.html', encoding='utf-8', errors='replace').read()

# full cam image list
cams = sorted(set(re.findall(r'https://www\.g24\.gal/prog24/ARQUIVO/CAMARAS_WEB/[\w\d_]+\.jpg', html)))
print('ARQUIVO cams:', len(cams))
for u in cams:
    print('  ', u.rsplit('/', 1)[1])

# pair images with nearby description text: split page by <img ...CAMARAS_WEB
parts = re.split(r'(?=<img[^>]+CAMARAS_WEB)', html)
print('\nblocks:', len(parts))
for p in parts[1:]:
    m = re.search(r'CAMARAS_WEB/([\w\d_]+)\.jpg', p)
    if not m:
        continue
    title = re.search(r'<h2[^>]*>(.*?)</h2>', p, re.S) or re.search(r'<h3[^>]*>(.*?)</h3>', p, re.S)
    desc = re.search(r'<p>(.*?)</p>', p, re.S)
    t = re.sub(r'<[^>]+>', '', title.group(1)).strip() if title else '?'
    d = re.sub(r'<[^>]+>', '', desc.group(1)).strip() if desc else ''
    print('  %-18s | %-45s | %s' % (m.group(1), t[:45], d[:90]))

# freshness probe: HEAD two cams twice
UA = 'Mozilla/5.0'
for u in (cams[0], cams[len(cams) // 2]):
    out = subprocess.run(
        ['curl', '-sIL', '-A', UA, '--max-time', '20', u],
        capture_output=True, text=True).stdout
    hdr = {k.lower(): v for k, v in re.findall(r'^([\w-]+): (.+)$', out, re.M)}
    print('\nHEAD', u)
    print('   last-modified:', hdr.get('last-modified'), '| etag:', hdr.get('etag'),
          '| len:', hdr.get('content-length'))
