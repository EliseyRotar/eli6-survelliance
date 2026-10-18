import json
import os
import re

cfg = json.load(open(os.environ['TEMP'] + r'\tiivii_cfg.json', encoding='utf-8'))
cams = cfg['cameras']
print('active cams:', len(cams))
rows = []
for c in cams:
    loc = c.get('location') or {}
    rows.append((c['name'], c.get('url'), loc.get('lat'), loc.get('lon'),
                 c.get('active'), c.get('error_status'), c.get('thumbnail')))
    print('%-16s | %-52s | %-10s %-11s | act=%-5s %-4s' % (
        c['name'], (c.get('url') or '')[:52], loc.get('lat'), loc.get('lon'),
        c.get('active'), c.get('error_status')))

static = re.findall(r'CAMARAS_WEB/([\w\d_]+)\.jpg',
                    open(os.environ['TEMP'] + r'\crtvg_cams.html',
                         encoding='utf-8', errors='replace').read())
static = sorted(set(static))
cfgnames = sorted(re.sub(r'[^a-z0-9]', '', (c['name'] or '').lower()) for c in cams)
print('\nstatic(30):', static)
print('cfg(26):   ', cfgnames)
# url slug is in m3u8 path
slugs = sorted(re.sub(r'[^a-z0-9]', '', (c.get('url') or '').split('/hls/')[-1].split('/')[0].lower())
               for c in cams if c.get('url'))
print('url slugs: ', slugs)
print('\nstatic not in slugs:', sorted(set(static) - set(slugs)))
print('slugs not in static:', sorted(set(slugs) - set(static)))
