import os
import re
import subprocess
import csv

TEMP = os.environ['TEMP']
ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'


def fetch(url, out, timeout=35):
    p = subprocess.run(['curl', '-sL', '-A', UA, '--max-time', str(timeout), '-o',
                        os.path.join(TEMP, out), '-w', '%{http_code}|%{size_download}',
                        url], capture_output=True, text=True, timeout=timeout + 10)
    try:
        return open(os.path.join(TEMP, out), encoding='utf-8', errors='replace').read()
    except OSError:
        return ''


for url, out in [
    ('https://www.webcammurcia.com/', 'wmc.html'),
    ('https://www.meteomurcia.com/webcam.php', 'mmu.html'),
    ('https://www.webcammurcia.com/airqual.html', 'wmc2.html'),
]:
    st = fetch(url, out)
    print('== %s ==' % url)
    h = open(os.path.join(TEMP, out), encoding='utf-8', errors='replace').read()
    print('  len', len(h))
    pats = {
        'img': r'<img[^>]+src=["\']([^"\']+)',
        'iframe': r'<iframe[^>]+src=["\']([^"\']+)',
        'm3u8': r'https?://[^"\'\s]+\.m3u8[^"\'\s]*',
        'youtube': r'(?:youtube\.com/embed/|youtu\.be/)([\w-]{11})',
        'cam-ish': r'https?://[^"\'\s]*(?:cam|stream|live|mjpg|snapshot)[^"\'\s]*',
        'js-files': r'src=["\']([^"\']+\.js[^"\']*)',
    }
    for k, p in pats.items():
        m = sorted(set(re.findall(p, h, re.I)))
        if m:
            print('  %s (%d):' % (k, len(m)))
            for x in m[:12]:
                print('    ', x[:150])

print('\n--- CSV overlap ---')
rows = list(csv.DictReader(open(ROOT + r'\controllable_Webcams.csv', newline='', encoding='utf-8')))
for needle in ('webcammurcia', 'meteomurcia', 'Avenida Libertad', 'Puente Tocinos',
               'Murcia'):
    hits = [r for r in rows if needle.lower() in ' '.join(
        (r.get(k) or '') for k in ('url', 'live_stream_url', 'notes', 'project_name',
                                   'description', 'city', 'region')).lower()]
    print('  %-18s -> %d %s' % (needle, len(hits),
          [(h['csv_id'], (h['project_name'] or '')[:28], (h['city'] or '')) for h in hits[:5]]))
