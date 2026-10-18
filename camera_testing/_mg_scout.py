import json
import os
import re
import subprocess

TEMP = os.environ['TEMP']
p = subprocess.run(
    ['curl', '-sL', '--max-time', '40', '-A', 'Mozilla/5.0',
     '-o', TEMP + r'\mg_ms.json', '-w', '%{http_code} %{size_download}',
     'https://ideg.xunta.gal/meteogalicia/rest/services/METEO2_WS/Camaras/MapServer?f=json'],
    capture_output=True, text=True)
print('mapserver:', p.stdout)
d = json.load(open(TEMP + r'\mg_ms.json', encoding='utf-8'))
for l in d.get('layers') or []:
    print('  layer', l.get('id'), l.get('name'))
if 'error' in d:
    print('ERROR', d['error'])

h = open(TEMP + r'\mg_page.html', encoding='utf-8', errors='replace').read()
srcs = re.findall(r'<script[^>]+src="([^"]+)"', h)
print('scripts:', srcs[:12])

# probe one image url from existing pattern
p2 = subprocess.run(
    ['curl', '-s', '-o', 'NUL', '-w', '%{http_code}|%{content_type}|%{size_download}',
     '--max-time', '25', '-A', 'Mozilla/5.0',
     'https://www.meteogalicia.gal/datosred/camaras/MeteoGalicia/Langosteira/ultima.jpg'],
    capture_output=True, text=True)
print('probe Langosteira ultima.jpg:', p2.stdout)
