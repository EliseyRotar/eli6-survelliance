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


print('chunk:', curl('https://www.meteogalicia.gal/web/chunk-5V3GQ723.js', TEMP + r'\mg_chunk.js'))
h = open(TEMP + r'\mg_chunk.js', encoding='utf-8', errors='replace').read()
print('len:', len(h))
# further lazy imports
print('imports:', sorted(set(re.findall(r'import\("\./([^"]+)"\)', h)))[:30])
for pat in ('camara', 'json', '.action', 'servizos', 'https://'):
    ms = [m.start() for m in re.finditer(re.escape(pat), h, re.I)]
    print('==', pat, len(ms))
    for i in ms[:8]:
        print('   ', h[max(0, i - 120):i + 160].replace('\n', ' ')[:270])
