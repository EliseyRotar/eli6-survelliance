import os
import re

for name in ('cuen_sm2.html', 'cuen_sm.html', 'cuen_pm.html'):
    p = os.path.join(os.environ['TEMP'], name)
    if not os.path.exists(p):
        print(name, 'missing')
        continue
    h = open(p, encoding='utf-8', errors='replace').read()
    urls = sorted(set(re.findall(r'https?://[^"\'\s<>]+', h)))
    keep = [u for u in urls if not any(
        d in u.lower() for d in (
            'google', 'gstatic', 'facebook', 'twitter', 'jquery', 'bootstrap',
            'fontawesome', 'insuit', 'w3.org', 'googletagmanager', 'schema.org',
            'pinterest', 'youtube.com/subscribe', 'instagram', 'linkedin'))]
    print('==', name, 'total', len(urls), 'kept', len(keep))
    for u in keep:
        print('  ', u[:170])
