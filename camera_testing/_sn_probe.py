import os
import re
import subprocess
import csv

TEMP = os.environ['TEMP']
ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'


def head(url, timeout=25):
    p = subprocess.run(['curl', '-sIL', '-A', UA, '--max-time', str(timeout),
                        '-w', '%{http_code}|%{content_type}|%{size_download}',
                        '-o', os.devnull, url],
                       capture_output=True, text=True, timeout=timeout + 10)
    return p.stdout.strip()


def get(url, out, timeout=30):
    p = subprocess.run(['curl', '-sL', '-A', UA, '--max-time', str(timeout), '-o',
                        os.path.join(TEMP, out), '-w', '%{http_code}|%{content_type}|%{size_download}',
                        url], capture_output=True, text=True, timeout=timeout + 10)
    return p.stdout.strip()


print('--- trafficvision mirrors ---')
for cid in (15110, 15112, 15111):
    print(' %d.mp4 -> %s' % (cid, head('https://media.trafficvision.live/feratel/%d.mp4' % cid)))

print('--- feratel thumbs/pics ---')
for url in ('https://wtvthmb.feratel.com/thumbnails/15110.jpeg?dcsdesign=1',
            'https://wtvthmb.feratel.com/thumbnails/15112.jpeg?dcsdesign=1',
            'https://webtvhotspot.feratel.com/hotspot/37/15110/2.jpeg?design=v3',
            'https://webtvhotspot.feratel.com/hotspot/37/15112/0.jpeg?design=v3'):
    print(' %s -> %s' % (url.split('/')[-1][:44], head(url)))

print('--- recursos.sierranevada snapshot ---')
print(' ', head('https://recursos.sierranevada.es/_extras/fotos_camaras/pradollano/snap_c1.jpg'))

print('--- DGT 313 confirm ---')
rows = list(csv.DictReader(open(ROOT + r'\controllable_Webcams.csv', newline='', encoding='utf-8')))
for r in rows:
    if r['csv_id'] == 'tv_108284':
        print(' tv_108284:', {k: (r.get(k) or '')[:80] for k in
                             ('project_name', 'url', 'live_stream_url', 'notes', 'lat', 'lon', 'city', 'live_status')})

# titles on official page: dump all "Title"-ish keys
html = open(TEMP + r'\sn_webcams.html', encoding='utf-8', errors='replace').read()
titles = re.findall(r'\\?"Title\\?":\s*\\?"([^"\\]{3,90})\\?"', html)
print('\npage Title keys:', len(titles))
for t in titles:
    print('  -', t)

# webtv player: any inline config?
w = open(TEMP + r'\feratel_webtv.html', encoding='utf-8', errors='replace').read()
print('\nwebtv <title>:', re.findall(r'<title>([^<]+)</title>', w))
for pat in (r'"(?:url|src|stream|file)"\s*:\s*"([^"]+)"', r'js/[\w./-]+\.js', r'api[\w./-]*'):
    m = sorted(set(re.findall(pat, w, re.I)))
    print(pat[:30], '->', m[:15])
