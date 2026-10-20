# -*- coding: utf-8 -*-
"""Session 48c: find Calgary cam slideshow/timelapse/archive endpoints.

1. calgary.ca page JS bundles: grep for timelapse/slideshow/historic/api.
2. trafficcam.calgary.ca archive path patterns.
3. Wayback CDX for loc jpgs (snapshot depth per cam).
4. 511.alberta.ca Cctv history feature.
"""
import json
import os
import re
import subprocess

TEMP = os.environ['TEMP']
ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'


def fetch(url, out=None, timeout=45):
    args = ['curl', '-sL', '-A', UA, '--max-time', str(timeout)]
    if out:
        args += ['-o', os.path.join(TEMP, out)]
    args += ['-w', '%{http_code}|%{content_type}|%{size_download}', url]
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout + 12)
    body = ''
    if out and os.path.exists(os.path.join(TEMP, out)):
        try:
            body = open(os.path.join(TEMP, out), encoding='utf-8', errors='replace').read()
        except OSError:
            pass
    return p.stdout.strip(), body


# 1) JS bundles on calgary.ca cam page
h = open(os.path.join(TEMP, 'calgary_cams.html'), encoding='utf-8', errors='replace').read()
js_urls = sorted(set(re.findall(r'src="([^"]+\.js[^"]*)"', h)))
print('js on page:', len(js_urls))
for u in js_urls:
    print(' ', u[:130])

# fetch same-origin js
for u in js_urls:
    if 'calgary.ca' in u or u.startswith('/'):
        full = u if u.startswith('http') else 'https://www.calgary.ca' + (u if u.startswith('/') else '/' + u)
        meta, js = fetch(full, out='page.js', timeout=30)
        if not js:
            continue
        hits = []
        for pat in (r'timelapse[^"\'\s,]{0,40}', r'slideshow[^"\'\s,]{0,40}',
                    r'historic\w*[^"\'\s,]{0,30}', r'archive[^"\'\s,]{0,30}',
                    r'history[^"\'\s,]{0,30}', r'trafficcam[^"\'\s]{0,60}',
                    r'camera[^"\'\s]{0,50}\.jpg', r'/api/[^"\'\s]{0,60}',
                    r'k7p9-kppz', r'loc\d+\.jpg'):
            m = sorted(set(re.findall(pat, js, re.I)))
            if m:
                hits.append((pat[:22], m[:10]))
        if hits:
            print('\nJS %s (%s):' % (full[-60:], meta))
            for pat, m in hits:
                print('  %s ->' % pat, [x[:90] for x in m])

# inline scripts in page
inline = re.findall(r'<script[^>]*>(.*?)</script>', h, re.S | re.I)
print('\ninline scripts:', len(inline))
for s in inline:
    for pat in (r'timelapse', r'slideshow', r'trafficcam', r'camera_url', r'k7p9', r'loc\d+', r'\.jpg'):
        if re.search(pat, s, re.I):
            print(' inline hit [%s]: %s' % (pat, re.sub(r'\s+', ' ', s)[:300]))
            break

# 2) archive path patterns on trafficcam host
print('\n--- archive patterns on loc86 ---')
for path in (
    '/loc86_1.jpg', '/loc86-1.jpg', '/loc86/1.jpg', '/loc86/0.jpg',
    '/loc86_0.jpg', '/archive/loc86.jpg', '/history/loc86.jpg',
    '/timelapse/loc86.jpg', '/loc86/prev.jpg', '/prev/loc86.jpg',
    '/loc86.jpg?n=1', '/loc86.jpg?frame=1', '/loc86.jpg?hour=1',
    '/thumbs/loc86.jpg', '/small/loc86.jpg', '/loc86_small.jpg',
    '/loc86_s.jpg', '/loc86_t.jpg', '/seq/loc86/1.jpg',
):
    meta, _ = fetch('https://trafficcam.calgary.ca' + path, timeout=10)
    code = meta.split('|')[0]
    if code not in ('404', '000', '403'):
        print(' %-28s -> %s' % (path, meta))
print(' (only non-404 shown)')

# 3) Wayback CDX for a few locs
print('\n--- Wayback CDX ---')
for loc in (86, 17, 223):
    url = 'https://web.archive.org/cdx/search/cdx?url=trafficcam.calgary.ca/loc%d.jpg&output=json&limit=20&fl=timestamp,statuscode,length' % loc
    meta, body = fetch(url, timeout=40)
    try:
        d = json.loads(body)
        rows = d[1:] if len(d) > 1 else []
        print(' loc%d: %d snapshots shown (meta %s)' % (loc, len(rows), meta))
        for r in rows[:6]:
            print('   ', r)
    except Exception as e:
        print(' loc%d fail: %s %r' % (loc, e, body[:120]))
