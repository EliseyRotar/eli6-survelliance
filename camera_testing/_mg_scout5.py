import re
import subprocess

import os
TEMP = os.environ['TEMP']
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'


def curl(url, out):
    p = subprocess.run(
        ['curl', '-sL', '--max-time', '60', '-A', UA, '-o', out,
         '-w', '%{http_code} %{size_download}', url],
        capture_output=True, text=True)
    return p.stdout


print('webcams chunk:', curl('https://www.meteogalicia.gal/web/chunk-A6AZO46B.js', TEMP + r'\mg_wc.js'))
h = open(TEMP + r'\mg_wc.js', encoding='utf-8', errors='replace').read()
print('len:', len(h))
for pat in ('camara', 'json', '.action', 'servizos', 'http', 'environment', 'apiUrl', 'assets'):
    ms = [m.start() for m in re.finditer(re.escape(pat), h, re.I)]
    if not ms:
        continue
    print('==', pat, len(ms))
    for i in ms[:10]:
        print('   ', h[max(0, i - 130):i + 170].replace('\n', ' ')[:290])
