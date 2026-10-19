import os
import re

TEMP = os.environ['TEMP']
for name in ('cuen_pm.html', 'cuen_sm.html'):
    h = open(os.path.join(TEMP, name), encoding='utf-8', errors='replace').read()
    print('===== %s =====' % name)
    # all local anchors
    for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', h, re.I | re.S):
        href, txt = m.group(1), re.sub(r'<[^>]+>', '', m.group(2)).strip()
        if any(k in href.lower() for k in ('webcam', 'camara', 'cam', 'live', 'miguel', 'plaza')):
            print('  link %-55s -> %s' % (href[:55], txt[:50]))
    # any .asp/.jpg/js vars
    for pat in (r'["\']([^"\']*\.asp[^"\']*)["\']', r'var\s+\w+\s*=\s*["\']([^"\']+)["\']',
                r'src=["\']([^"\']*(?:live|cam|jpg)[^"\']*)["\']'):
        for x in sorted(set(re.findall(pat, h, re.I))):
            if not any(y in x.lower() for y in ('googletag', 'jquery', 'bootstrap', 'facebook', 'twitter',
                                                'portal', 'logo', 'icon', 'flag', 'css', '.js')):
                print('  %s -> %s' % (pat[:20], x[:110]))
