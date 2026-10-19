import os
import re
import subprocess
import csv

TEMP = os.environ['TEMP']
ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'

# 1) CSV: which of 15110..15114 exist (any form)
rows = list(csv.DictReader(open(ROOT + r'\controllable_Webcams.csv', newline='', encoding='utf-8')))
for cid in range(15110, 15115):
    hits = [r for r in rows if str(cid) in ' '.join(
        (r.get(k) or '') for k in ('url', 'live_stream_url', 'notes', 'project_name'))]
    print('CSV %d -> %d %s' % (cid, len(hits),
          [(h['csv_id'], (h['project_name'] or '')[:28],
            (h['live_stream_url'] or h['url'] or '')[:60]) for h in hits[:3]]))

# 2) titles from sierranevada page JSON blocks
html = open(TEMP + r'\sn_webcams.html', encoding='utf-8', errors='replace').read()
print('\n--- page JSON title/iframe pairing ---')
# blocks like {"...":{"Title":"..","Values":{"iframe":"..cam=NNNNN.."}}
for m in re.finditer(r'cam=(15\d{3})', html):
    s = max(0, m.start() - 4000)
    seg = html[s:m.start()]
    titles = re.findall(r'\\?"(?:Title|title|Nombre)\\?":\s*\\?"([^"\\]{3,80})\\?"', seg)
    print('  cam=%s near-titles=%s' % (m.group(1), titles[-3:]))

# 3) fetch one webtv player to learn its data endpoints
p = subprocess.run(['curl', '-sL', '-A', UA, '--max-time', '40', '-o',
                    TEMP + r'\feratel_webtv.html', '-w', '%{http_code}|%{size_download}',
                    'https://webtv.feratel.com/webtv/?design=v5&cam=15110&c1=0'],
                   capture_output=True, text=True, timeout=60)
print('\nwebtv:', p.stdout)
w = open(TEMP + r'\feratel_webtv.html', encoding='utf-8', errors='replace').read()
print('webtv len', len(w))
for pat in (r'https?://[^"\'\s]+\.m3u8[^"\'\s]*',
            r'https?://[^"\'\s]+\.(?:mp4|jpeg|jpg)[^"\'\s]*',
            r'hotspot[^"\'\s]*',
            r'source\s*src="([^"]+)"'):
    m = sorted(set(re.findall(pat, w, re.I)))
    print(pat[:40], len(m))
    for x in m[:12]:
        print('   ', x[:150])
