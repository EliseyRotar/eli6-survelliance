# -*- coding: utf-8 -*-
"""Session 48c: extract /ss/ slideshow URL template from map JS + probe."""
import os
import re
import subprocess

TEMP = os.environ['TEMP']
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'


def fetch(url, timeout=30, binary=False):
    op = os.path.join(TEMP, 'js_probe.bin')
    p = subprocess.run(['curl', '-sL', '-A', UA, '--max-time', str(timeout),
                        '-o', op, '-w', '%{http_code}|%{content_type}|%{size_download}', url],
                       capture_output=True, text=True, timeout=timeout + 10)
    body = b''
    if os.path.exists(op):
        with open(op, 'rb') as f:
            body = f.read()
    if binary:
        return p.stdout.strip(), body
    return p.stdout.strip(), body.decode('utf-8', 'replace')


meta, js = fetch('https://www.calgary.ca/etc/clientlibs/www/components/content/map_modular/map_modular/clientlibs.min.js')
print('map js:', meta, 'len', len(js))

for needle in ('ss/', 'Slideshow', 'slideshow', 'trafficcam', 'cameraOffline', 'loc', 'frame', 'hour', 'timestamp', 'sequence', 'interval', 'setInterval', 'imgUrl', 'imageUrl'):
    for m in re.finditer(re.escape(needle), js):
        s = max(0, m.start() - 260)
        e = min(len(js), m.end() + 260)
        ctx = js[s:e]
        if 'trafficcam' in ctx or 'slideshow' in ctx.lower() or 'loc' in ctx:
            print('\n[%s] …%s…' % (needle, ctx.replace('\n', ' ')[:480]))
            break  # first meaningful context per needle

# also traffic-cam-accordion js
meta2, js2 = fetch('https://www.calgary.ca/etc/clientlibs/www/components/content/traffic-cam-accordion/clientlibs.min.js')
print('\n\naccordion js:', meta2, 'len', len(js2))
for needle in ('ss/', 'slideshow', 'trafficcam', 'loc', 'cameraOffline', 'modal', 'image', 'jpg'):
    for m in re.finditer(re.escape(needle), js2, re.I):
        s = max(0, m.start() - 240)
        e = min(len(js2), m.end() + 240)
        print('\n[%s] …%s…' % (needle, js2[s:e].replace('\n', ' ')[:460]))
        break
