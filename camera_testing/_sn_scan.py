import os
import re
import subprocess

TEMP = os.environ['TEMP']
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
p = subprocess.run(['curl', '-sL', '-A', UA, '--max-time', '40', '-o',
                    TEMP + r'\sn_webcams.html', '-w', '%{http_code}|%{size_download}',
                    'https://sierranevada.es/es/invierno/la-estacion/en-directo/webcams/'],
                   capture_output=True, text=True, timeout=60)
print('sn:', p.stdout)

html = open(TEMP + r'\sn_webcams.html', encoding='utf-8', errors='replace').read()
print('len', len(html))
pats = {
    'img': r'<img[^>]+src="([^"]+)"',
    'data-src': r'data-src="([^"]+)"',
    'iframe': r'<iframe[^>]+src="([^"]+)"',
    'm3u8': r'https?://[^"\'\s]+\.m3u8[^"\'\s]*',
    'cam-ish': r'https?://[^"\'\s]*(?:cam|stream|live)[^"\'\s]*',
    'jpg-ish': r'https?://[^"\'\s]+\.jpg[^"\'\s]*',
}
for k, ptt in pats.items():
    m = sorted(set(re.findall(ptt, html, re.I)))
    print('%s: %d' % (k, len(m)))
    for x in m[:25]:
        print('   ', x[:170])
