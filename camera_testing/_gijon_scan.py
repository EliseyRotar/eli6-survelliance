import os
import re

html = open(os.environ['TEMP'] + r'\gijon_webcams.html', encoding='utf-8', errors='replace').read()
print('len', len(html))
m = re.search(r'<title>(.*?)</title>', html, re.S)
print('title:', (m.group(1).strip() if m else '?')[:120])

# iframe/embeds
for pat in (r'<iframe[^>]+src="([^"]+)"', r'data-src="([^"]+)"'):
    for s in sorted(set(re.findall(pat, html))):
        if any(k in s.lower() for k in ('cam', 'webcam', 'stream', 'live', 'm3u8', 'jpg', 'png', 'embed')):
            print('embed:', s)

# cam image/stream urls
urls = sorted(set(re.findall(r'https?://[^"\'\s<>]+\.(?:jpg|jpeg|png|m3u8)[^"\'\s<>]*', html, re.I)))
print('media urls:', len(urls))
for u in urls[:40]:
    print('  ', u)

# text blocks mentioning webcam
for m in re.finditer(r'webcam', html, re.I):
    s = max(0, m.start() - 150)
    seg = re.sub(r'\s+', ' ', html[s:m.start() + 250])
    seg = re.sub(r'<[^>]+>', ' ', seg)
    print('ctx>', ' '.join(seg.split())[:260])
