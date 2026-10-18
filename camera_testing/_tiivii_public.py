import os
import re

html = open(os.environ['TEMP'] + r'\tiivii_public.html', encoding='utf-8', errors='replace').read()
print('len', len(html))
# tenant links / hostnames
hosts = sorted(set(re.findall(r'https?://([\w.-]+\.(?:tiivii\.com|[a-z0-9-]+\.[a-z]{2,}))', html)))
print('hosts:', len(hosts))
for h in hosts[:60]:
    print('  ', h)
# script/json assets
assets = sorted(set(re.findall(r'["\']([^"\']+\.(?:json|js))["\']', html)))
print('assets:', len(assets))
for a in assets[:30]:
    print('  ', a)
# any anchors
links = sorted(set(re.findall(r'href="([^"]+)"', html)))
print('hrefs:', len(links))
for l in links[:50]:
    print('  ', l[:140])
# text hints
m = re.search(r'<title>(.*?)</title>', html, re.S)
print('title:', m.group(1) if m else '?')
