# -*- coding: utf-8 -*-
"""Session 48c: probe /ss/<0..9>/locN.jpg historical frames + spacing."""
import hashlib
import os
import subprocess

TEMP = os.environ['TEMP']
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'


def get(url, out, timeout=20):
    op = os.path.join(TEMP, out)
    p = subprocess.run(['curl', '-sL', '-A', UA, '--max-time', str(timeout),
                        '-o', op, '-w', '%{http_code}|%{content_type}|%{size_download}',
                        '-D', os.path.join(TEMP, 'hdrs.txt'), url],
                       capture_output=True, text=True, timeout=timeout + 8)
    lm = ''
    try:
        for line in open(os.path.join(TEMP, 'hdrs.txt'), encoding='latin-1'):
            if line.lower().startswith('last-modified'):
                lm = line.split(':', 1)[1].strip()
    except OSError:
        pass
    prev = b''
    if os.path.exists(op):
        with open(op, 'rb') as f:
            prev = f.read()
    return p.stdout.strip(), lm, prev


print('loc86 slideshow frames:')
hashes = {}
for i in list(range(10)) + ['live']:
    path = 'loc86.jpg' if i == 'live' else 'ss/%d/loc86.jpg' % i
    meta, lm, body = get('https://trafficcam.calgary.ca/' + path, 'ss_%s.jpg' % i)
    h = hashlib.md5(body).hexdigest()[:10] if body else ''
    hashes[str(i)] = h
    print('  ss/%-4s -> %s lm=%s md5=%s bytes=%d jpeg=%s' % (
        i, meta, lm[:24], h, len(body), body[:2] == b'\xff\xd8'))

print('\nunique frames:', len(set(hashes.values())), '/', len(hashes))

# spot-check a couple more cams
for loc in (17, 223):
    print('\nloc%d:' % loc)
    seen = set()
    for i in (0, 5, 9):
        meta, lm, body = get('https://trafficcam.calgary.ca/ss/%d/loc%d.jpg' % (i, loc),
                             'ssx_%d_%d.jpg' % (loc, i))
        h = hashlib.md5(body).hexdigest()[:10] if body else ''
        seen.add(h)
        print('  ss/%d -> %s lm=%s md5=%s jpeg=%s' % (i, meta, lm[:24], h, body[:2] == b'\xff\xd8'))
