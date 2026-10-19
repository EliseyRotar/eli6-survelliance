# -*- coding: utf-8 -*-
"""Session 48: gap-id probes + ATIS/extra-source hunt + freshness."""
import hashlib
import json
import os
import re
import subprocess
import time

TEMP = os.environ['TEMP']
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'


def get_meta(url, timeout=20, out='probe.bin'):
    op = os.path.join(TEMP, out)
    p = subprocess.run(['curl', '-sL', '-A', UA, '--max-time', str(timeout),
                        '-o', op, '-w', '%{http_code}|%{content_type}|%{size_download}',
                        url], capture_output=True, text=True, timeout=timeout + 8)
    prev = b''
    if os.path.exists(op):
        with open(op, 'rb') as f:
            prev = f.read(160)
    return p.stdout.strip(), prev


print('--- 7 gap loc ids ---')
for i in (10, 109, 118, 159, 169, 171, 210):
    meta, prev = get_meta('https://trafficcam.calgary.ca/loc%d.jpg' % i, 15)
    print(' loc%d.jpg -> %s jpeg=%s' % (i, meta, prev[:2] == b'\xff\xd8'))

print('\n--- freshness 90s apart (loc86) ---')
digs = []
for k in range(2):
    meta, _ = get_meta('https://trafficcam.calgary.ca/loc86.jpg', 15, out='fresh.bin')
    with open(os.path.join(TEMP, 'fresh.bin'), 'rb') as f:
        body = f.read()
    digs.append((meta, hashlib.md5(body).hexdigest()[:10]))
    if k == 0:
        time.sleep(90)
print(' ', digs)

# calgary.ca page: ATIS link + any cam image urls
h = open(os.path.join(TEMP, 'calgary_cams.html'), encoding='utf-8', errors='replace').read()
print('\n--- calgary_cams.html markers ---')
for pat in (r'https?://[^"\'\s<>]*(?:atis|ATIS)[^"\'\s<>]*', r'href="([^"]*(?:atis|camera|cam)[^"]*)"',
            r'https?://trafficcam[^"\'\s<>]+', r'https?://[^"\'\s<>]+\.jpg'):
    m = sorted(set(re.findall(pat, h, re.I)))
    if m:
        print(' %s ->' % pat[:34], [x[:110] for x in m[:12]])

# trafficcalgary.ca: what sources?
h2 = open(os.path.join(TEMP, 'tcagary.html'), encoding='utf-8', errors='replace').read()
print('\n--- trafficcalgary.ca sources ---')
for pat in (r'https?://[^"\'\s<>]+\.jpg[^"\'\s<>]*', r'https?://[^"\'\s<>]*(?:511|alberta|drive)[^"\'\s<>]*',
            r'src="([^"]+\.js[^"]*)"', r'fetch\(([^)]+)\)', r'api[^"\'\s]{0,60}'):
    m = sorted(set(re.findall(pat, h2, re.I)))
    if m:
        print(' %s ->' % pat[:30], [x[:130] for x in m[:14]])
