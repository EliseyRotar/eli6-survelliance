# -*- coding: utf-8 -*-
"""Session 48: Calgary live-variant probes (binary-safe) + extra source hunt."""
import json
import os
import re
import subprocess

TEMP = os.environ['TEMP']
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'


def head(url, timeout=15):
    p = subprocess.run(['curl', '-sIL', '-A', UA, '--max-time', str(timeout), url],
                       capture_output=True, text=True, timeout=timeout + 8)
    lines = [l.strip() for l in (p.stdout or '').splitlines()
             if l.lower().startswith(('http/', 'content-type', 'content-length',
                                      'last-modified', 'location'))]
    return ' | '.join(lines)


def get_meta(url, timeout=20, out='probe.bin'):
    op = os.path.join(TEMP, out)
    p = subprocess.run(['curl', '-sL', '-A', UA, '--max-time', str(timeout),
                        '-o', op, '-w', '%{http_code}|%{content_type}|%{size_download}',
                        url], capture_output=True, text=True, timeout=timeout + 8)
    body_preview = b''
    if os.path.exists(op):
        with open(op, 'rb') as f:
            body_preview = f.read(200)
    return p.stdout.strip(), body_preview


cams = json.load(open(os.path.join(TEMP, 'k7p9-kppz.json'), encoding='utf-8'))
print('dataset cams:', len(cams))
# collect loc ids
locs = []
for c in cams:
    u = (c.get('camera_url') or {}).get('url', '')
    m = re.search(r'loc(\d+)\.jpg', u)
    if m:
        locs.append(int(m.group(1)))
print('loc ids: n=%d min=%d max=%d' % (len(locs), min(locs), max(locs)))
missing = sorted(set(range(min(locs), max(locs) + 1)) - set(locs))
print('gaps in range:', len(missing), missing[:40])

print('\n--- variant probes on loc86 + others ---')
for i in (86, 87, 1, max(locs)):
    for suffix in ('.m3u8', '.mjpg', '.mjpeg', '.mp4', '.ts', '.gif', '.png'):
        meta, prev = get_meta('https://trafficcam.calgary.ca/loc%d%s' % (i, suffix), 12)
        code = meta.split('|')[0]
        if code not in ('404', '000'):
            print(' loc%d%s -> %s %r' % (i, suffix, meta, prev[:60]))
    for path in ('/loc%d/' % i, '/loc%d/video' % i, '/loc%d/index.m3u8' % i,
                 '/hls/loc%d/index.m3u8' % i, '/live/loc%d' % i):
        meta, prev = get_meta('https://trafficcam.calgary.ca%s' % path, 12)
        code = meta.split('|')[0]
        if code not in ('404', '000'):
            print(' %s -> %s %r' % (path, meta, prev[:60]))

print('\n--- root/site pages ---')
for path in ('/', '/index.html', '/map.html', '/mobile/', '/list.html', '/cameras.html'):
    meta, prev = get_meta('https://trafficcam.calgary.ca%s' % path, 15,
                          out='root.bin')
    print(' %-16s -> %s %r' % (path, meta, prev[:120]))

print('\n--- header of one real jpg ---')
meta, prev = get_meta('https://trafficcam.calgary.ca/loc%d.jpg' % 86, 15, out='loc86.jpg')
print(' loc86.jpg:', meta, 'jpeg' if prev[:2] == b'\xff\xd8' else prev[:20])

print('\n--- freshness: two pulls 20s apart ---')
import hashlib
import time
digs = []
for k in range(2):
    meta, _ = get_meta('https://trafficcam.calgary.ca/loc86.jpg', 15, out='fresh.bin')
    with open(os.path.join(TEMP, 'fresh.bin'), 'rb') as f:
        digs.append((meta, hashlib.md5(f.read()).hexdigest()[:10]))
    if k == 0:
        time.sleep(20)
print(' ', digs)
