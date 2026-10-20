# -*- coding: utf-8 -*-
"""Session 48c: extract /ss/ slideshow template (correct clientlib path)."""
import os
import re
import subprocess

TEMP = os.environ['TEMP']
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'


def fetch(url, timeout=30):
    op = os.path.join(TEMP, 'js_probe.bin')
    p = subprocess.run(['curl', '-sL', '-A', UA, '--max-time', str(timeout),
                        '-o', op, '-w', '%{http_code}|%{content_type}|%{size_download}', url],
                       capture_output=True, text=True, timeout=timeout + 10)
    body = b''
    if os.path.exists(op):
        with open(op, 'rb') as f:
            body = f.read()
    return p.stdout.strip(), body.decode('utf-8', 'replace')


meta, js = fetch('https://www.calgary.ca/etc.clientlibs/www/components/content/map_modular/map_modular/clientlibs.min.js')
print('map js:', meta, 'len', len(js))

# save for reference
open(os.path.join(TEMP, 'map_modular.js'), 'w', encoding='utf-8').write(js)

# all trafficcam contexts
print('\n=== all trafficcam contexts ===')
for m in re.finditer(r'trafficcam', js, re.I):
    s = max(0, m.start() - 350)
    e = min(len(js), m.end() + 350)
    print('\n…%s…' % js[s:e].replace('\n', ' ')[:700])

print('\n=== /ss/ contexts ===')
for m in re.finditer(r'/ss/', js):
    s = max(0, m.start() - 300)
    e = min(len(js), m.end() + 300)
    print('\n…%s…' % js[s:e].replace('\n', ' ')[:600])

print('\n=== SlideshowViewer class ===')
m = re.search(r'SlideshowViewer[^\n]{0,80}class|class[^\n]{0,40}SlideshowViewer', js)
if m:
    s = max(0, m.start() - 100)
    print(js[s:s + 1600])
