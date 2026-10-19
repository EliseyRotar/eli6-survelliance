import json
import os
import re
import subprocess
import csv
from datetime import datetime, timezone

TEMP = os.environ['TEMP']
ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'


def fetch(url, out=None, timeout=30):
    args = ['curl', '-sL', '-A', UA, '--max-time', str(timeout)]
    if out:
        args += ['-o', os.path.join(TEMP, out)]
    args += ['-D', '-', '-w', '|%{http_code}|%{content_type}|%{size_download}', url]
    p = subprocess.run(args, capture_output=True, timeout=timeout + 10)
    raw = p.stdout.decode('latin-1', 'replace')
    body = ''
    if out:
        try:
            body = open(os.path.join(TEMP, out), encoding='utf-8', errors='replace').read()
        except OSError:
            pass
    else:
        parts = raw.rsplit('|', 3)
        body = parts[0] if len(parts) == 4 else raw
    lm = re.search(r'[Ll]ast-[Mm]odified:\s*([^\r\n]+)', raw)
    code_m = re.search(r'\|(\d{3})\|([^|]*)\|(\d+)$', raw)
    return {
        'lm': lm.group(1).strip() if lm else None,
        'code': code_m.group(1) if code_m else '?',
        'ctype': code_m.group(2) if code_m else '?',
        'size': code_m.group(3) if code_m else '?',
        'body': body,
    }


print('--- tv_143516 state ---')
rows = list(csv.DictReader(open(ROOT + r'\controllable_Webcams.csv', newline='', encoding='utf-8')))
for r in rows:
    if r['csv_id'] == 'tv_143516':
        print({k: (r.get(k) or '')[:90] for k in (
            'project_name', 'url', 'live_stream_url', 'type', 'live_status',
            'http_status', 'content_type', 'lat', 'lon', 'city', 'org',
            'geo_source', 'notes')})

print('\n--- avlibertad.jpg freshness (two probes) ---')
for i in (1, 2):
    r = fetch('https://www.webcammurcia.com/avlibertad.jpg', 'avlib1.jpg' if i == 1 else 'avlib2.jpg')
    print(' probe%d: code=%s size=%s lm=%s' % (i, r['code'], r['size'], r['lm']))
    if i == 1:
        import time
        time.sleep(20)

print('\n--- windy cam page ---')
r = fetch('https://www.windy.com/-Webcams-Spain-Murcia--1334517004?1334517004', 'windy_murcia.html', 35)
print(' windy: code=%s size=%s' % (r['code'], r['size']))

print('\n--- camsecure pages ---')
for name in ('wmcam', 'xmcam'):
    r = fetch('https://www.camsecure.co.uk/webcam/murcia/%s.html' % name, '%s.html' % name)
    print(' %s: code=%s lm=%s' % (name, r['code'], r['lm']))
    h = r['body']
    for pat in (r'<img[^>]+src=["\']([^"\']+)', r'mjpeg[^"\'\s]*', r'\.m3u8[^"\'\s]*',
                r'https?://[^"\'\s]+\.(?:jpg|jpeg)[^"\'\s]*', r'file=["\']([^"\']+)',
                r'src=["\']([^"\']+)'):
        m = sorted(set(re.findall(pat, h, re.I)))
        if m:
            print('   %s ->' % pat[:22], [x[:110] for x in m[:8]])

print('\n--- youtube oembed/live ---')
for yid in ('CGNR241h08Q', 'L1rgJ3gI2Eg'):
    r = fetch('https://www.youtube.com/oembed?url=https://www.youtube.com/watch%%3Fv%%3D%s&format=json' % yid)
    try:
        oe = json.loads(r['body'])
        print(' %s: %s | %s' % (yid, oe.get('title'), oe.get('author_name')))
    except Exception as e:
        print(' %s: err %s code=%s' % (yid, e, r['code']))
    w = fetch('https://www.youtube.com/watch?v=%s' % yid, 'yt_%s.html' % yid, 35)
    html = w['body']
    live = '"isLive":true' in html or '"isLiveContent":true' in html
    ch = re.findall(r'"channelId":"(UC[\w-]{22})"', html)
    print('    live=%s channel=%s code=%s' % (live, sorted(set(ch))[:2], w['code']))
