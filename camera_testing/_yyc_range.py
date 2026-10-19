# -*- coding: utf-8 -*-
"""Session 48: full range probe 0..250 + fetch calgary.ca page + aggregator."""
import json
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

TEMP = os.environ['TEMP']
ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'


def get(url, out=None, timeout=45):
    args = ['curl', '-sL', '-A', UA, '--max-time', str(timeout)]
    if out:
        args += ['-o', os.path.join(TEMP, out)]
    args += ['-w', '%{http_code}|%{content_type}|%{size_download}', url]
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout + 10)
    return p.stdout.strip()


def probe(i):
    p = subprocess.run(['curl', '-sIL', '-A', UA, '--max-time', '12',
                        'https://trafficcam.calgary.ca/loc%d.jpg' % i],
                       capture_output=True, text=True, timeout=20)
    st = ''
    ct = ''
    cl = ''
    for l in (p.stdout or '').splitlines():
        ll = l.lower()
        if ll.startswith('http/'):
            st = l.split()[1]
        elif ll.startswith('content-type:'):
            ct = l.split(':', 1)[1].strip()
        elif ll.startswith('content-length:'):
            cl = l.split(':', 1)[1].strip()
    return i, st, ct, cl


results = {}
with ThreadPoolExecutor(max_workers=8) as ex:
    futs = [ex.submit(probe, i) for i in range(0, 251)]
    for f in as_completed(futs):
        i, st, ct, cl = f.result()
        if st == '200' and 'image' in ct:
            results[i] = cl
alive = sorted(results)
print('range 0..250: alive %d, dead %d' % (len(alive), 251 - len(alive)))
print('alive:', alive)
dead = [i for i in range(0, 251) if i not in results]
print('dead:', dead)

# try beyond max
print('\nbeyond 250:')
for i in (251, 255, 260, 280, 300):
    r = probe(i)
    print(' loc%d -> %s %s' % (r[0], r[1], r[2]))

# fetch calgary.ca page
print('\ncalgary.ca:', get('https://www.calgary.ca/roads/conditions/traffic-cameras.html',
                          out='calgary_cams.html', timeout=45))
# ATIS page
print('ATIS page:', get('https://www.calgary.ca/roads/conditions/advanced-traveller-information-system.html',
                        out='calgary_atis.html', timeout=45))
# aggregator
print('trafficcalgary.ca:', get('https://trafficcalgary.ca/', out='tcagary.html', timeout=45))

json.dump({'alive': alive, 'dead': dead, 'headers': results},
          open(os.path.join(TEMP, 'yyc_range.json'), 'w'), indent=1)
