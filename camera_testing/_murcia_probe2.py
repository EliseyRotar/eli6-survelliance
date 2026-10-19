import os
import re
import subprocess
import csv
import json

TEMP = os.environ['TEMP']
ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'


def fetch(url, out=None, timeout=25):
    args = ['curl', '-sL', '-A', UA, '--max-time', str(timeout)]
    if out:
        args += ['-o', os.path.join(TEMP, out)]
    args += ['-w', '%{http_code}|%{content_type}|%{size_download}', url]
    p = subprocess.run(args, capture_output=True, timeout=timeout + 10)
    meta = p.stdout.decode('latin-1', 'replace').strip()
    body = ''
    if out:
        try:
            body = open(os.path.join(TEMP, out), encoding='utf-8', errors='replace').read()
        except OSError:
            pass
    else:
        body = p.stdout.decode('utf-8', 'replace')
    return meta, body


print('--- camsecure m3u8 ---')
for name in ('murcia', 'murcia2'):
    meta, body = fetch('https://camsecure.co/HLS/%s.m3u8' % name)
    print(' %s.m3u8 -> %s' % (name, meta))
    print('   body[:200]:', repr(body[:200]))

print('\n--- YT titles from saved watch pages ---')
for yid in ('CGNR241h08Q', 'L1rgJ3gI2Eg'):
    html = open(os.path.join(TEMP, 'yt_%s.html' % yid), encoding='utf-8', errors='replace').read()
    og = re.findall(r'<meta property="og:title" content="([^"]+)"', html)
    t = re.findall(r'"videoPrimaryInfoRenderer".{0,400}?"text":"([^"]+)"', html)
    own = re.findall(r'"ownerChannelName":"([^"]+)"', html)
    print(' %s: og=%s | title=%s | owner=%s' % (yid, og[:1], t[:1], own[:1]))

print('\n--- CSV overlap exact ---')
rows = list(csv.DictReader(open(ROOT + r'\controllable_Webcams.csv', newline='', encoding='utf-8')))
for needle in ('camsecure', 'murcia.m3u8', 'murcia2.m3u8', 'CGNR241h08Q', 'L1rgJ3gI2Eg',
               'UCG3TWlJ9eh4n7-zNXNfPISg'):
    hits = [r for r in rows if needle.lower() in ' '.join(
        (r.get(k) or '') for k in ('url', 'live_stream_url', 'notes', 'project_name',
                                   'description')).lower()]
    print('  %-24s -> %d %s' % (needle, len(hits),
          [(h['csv_id'], (h['project_name'] or '')[:34]) for h in hits[:4]]))

from collections import Counter
print(' Murcia region vocab:', Counter(r['region'] for r in rows if 'murcia' in (r['region'] or '').lower()).most_common())
