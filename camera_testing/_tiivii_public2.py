import os
import re

html = open(os.environ['TEMP'] + r'\tiivii_public.html', encoding='utf-8', errors='replace').read()
print('--- hx/src/action endpoints ---')
for m in sorted(set(re.findall(r'(?:hx-get|hx-post|hx-src|src|action)="([^"]+)"', html))):
    print('  ', m)
print('--- context around tenant/camviewer words ---')
for w in ('camviewer', 'tenant', 'instalad', 'cliente', 'c maras', 'webcams/'):
    for m in re.finditer(w, html, re.I):
        s = max(0, m.start() - 90)
        seg = html[s:m.start() + 160].replace('\n', ' ')
        print(' %s > %s' % (w, seg[:240]))
