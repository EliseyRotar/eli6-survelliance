import re, json, collections, os, sys

D = os.path.dirname(os.path.abspath(__file__))
home = open(os.path.join(D, 'home_en.html'), encoding='utf-8', errors='replace').read()

print('=== HOSTS ===')
hosts = collections.Counter(re.findall(r'https?://([a-z0-9][a-z0-9.\-]+)', home, re.I))
for h, c in hosts.most_common(50):
    print(f'  {h}  x{c}')

print('=== API-LIKE STRINGS ===')
apis = collections.Counter(re.findall(r'["\']([^"\'\s]*(?:api|graphql|\.json)[^"\'\s]*)["\']', home, re.I))
for a, c in apis.most_common(40):
    print(f'  {a[:160]}  x{c}')

print('=== JS MODULES ===')
mods = sorted(set(re.findall(r'/_astro/[A-Za-z0-9._\-]+\.js', home)))
for m in mods[:60]:
    print('  ', m)
print('total modules:', len(mods))

print('=== TRAFFICVISION / WT ===')
tv = sorted(set(re.findall(r'[a-z0-9.\-]*(?:trafficvision|wtv|webtv)[a-z0-9.\-]*\.[a-z0-9.\-]+', home, re.I)))
for t in tv:
    print('  ', t)

print('=== EMBEDDED JSON KEYS (window.* / data-*) ===')
for m in sorted(set(re.findall(r'window\.([A-Z_][A-Z0-9_]{2,})\s*=', home)))[:30]:
    print('  window.' + m)
for m in sorted(set(re.findall(r'data-(?:config|props)="[^"]{0,80}', home)))[:15]:
    print('  ', m.replace('\n', ' ')[:140])

# sitemap parse
sm = open(os.path.join(os.environ.get('TEMP', '.'), 'feratel_sitemap0.xml'), encoding='utf-8', errors='replace').read()
locs = re.findall(r'<loc>(.*?)</loc>', sm)
en = [u for u in locs if '/en/webcams/' in u]
leaf = [u for u in en if re.search(r'-\d{3,6}$', u.split('?')[0])]
print(f'=== SITEMAP: total={len(locs)} en_webcams={len(en)} leaf_cams={len(leaf)}')
countries = collections.Counter(u.split('/en/webcams/')[1].split('/')[0] for u in leaf)
for c, n in countries.most_common():
    print(f'  {c}: {n}')
open(os.path.join(D, 'cam_urls.txt'), 'w').write('\n'.join(sorted(set(leaf))))
print('wrote cam_urls.txt:', len(set(leaf)))
