import json
import os
import re
import subprocess

TEMP = os.environ['TEMP']
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'


def curl(url, out, extra=()):
    p = subprocess.run(
        ['curl', '-sL', '--max-time', '60', '-A', UA, *extra, '-o', out,
         '-w', '%{http_code} %{size_download}', url],
        capture_output=True, text=True)
    return p.stdout


# 1. exact feature count
print('countOnly:',
      curl('https://ideg.xunta.gal/meteogalicia/rest/services/METEO2_WS/Camaras/MapServer/0/query?where=1%3D1&returnCountOnly=true&f=json',
           TEMP + r'\mg_count.json'))
print(' ->', open(TEMP + r'\mg_count.json', encoding='utf-8').read()[:200])

# 2. SPA bundle candidates
for base in ('https://www.meteogalicia.gal/web/observacion/',
             'https://www.meteogalicia.gal/web/',
             'https://www.meteogalicia.gal/'):
    url = base + 'main-QEGW3TMS.js'
    r = curl(url, TEMP + r'\mg_main.js')
    print('bundle', r, url)
    if r.startswith('200'):
        break
h = open(TEMP + r'\mg_main.js', encoding='utf-8', errors='replace').read()
print('bundle len:', len(h))
for pat in ('jsonCamaras', 'camaras.action', 'servizos', 'observacion/json', 'listaCamaras', 'ultima.jpg', 'camaras/', 'FeatureServer', 'ideg'):
    ms = [m.start() for m in re.finditer(re.escape(pat), h)]
    if ms:
        print('==', pat, len(ms))
        for i in ms[:3]:
            print('   ', h[max(0, i - 140):i + 200].replace('\n', ' ')[:330])
