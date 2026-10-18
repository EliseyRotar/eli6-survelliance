import re
import subprocess

import os
TEMP = os.environ['TEMP']
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'


def head(url):
    p = subprocess.run(
        ['curl', '-s', '-o', 'NUL', '-w', '%{http_code}|%{content_type}|%{size_download}',
         '--max-time', '25', '-A', UA, url],
        capture_output=True, text=True)
    return p.stdout


for d in ('Fontaneira', 'Lira', 'CiesFaroSur', 'Onsplaya', 'Xesteiras', 'Radar',
          'Ribadeoporto', 'Santiago', 'Muros', 'Aguete2'):
    print('%-14s %s' % (d, head('https://www.meteogalicia.gal/datosred/camaras/MeteoGalicia/%s/ultima.jpg' % d)))
print('%-14s %s' % ('MedioRural/Muros', head('https://www.meteogalicia.gal/datosred/camaras/MedioRural/Muros/ultima.jpg')))

h = open(TEMP + r'\mg_main.js', encoding='utf-8', errors='replace').read()
# angular lazy chunk names
chunks = sorted(set(re.findall(r'"([a-z0-9\-]*(?:camara|observ|rss|serviz)[a-z0-9\-]*-[A-Z0-9]+\.js)"', h, re.I)))
print('chunks:', chunks[:20])
for pat in ('.action', 'jsonCamaras', 'observacion', 'camaras'):
    ms = [m.start() for m in re.finditer(re.escape(pat), h)]
    print(pat, len(ms))
    for i in ms[:6]:
        print('   ', h[max(0, i - 100):i + 140].replace('\n', ' ')[:230])
