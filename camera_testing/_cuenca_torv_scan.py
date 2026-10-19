import csv
import os
import re
import subprocess

TEMP = os.environ['TEMP']
ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'


def fetch(url, out, timeout=35):
    p = subprocess.run(['curl', '-sL', '-A', UA, '--max-time', str(timeout), '-o',
                        os.path.join(TEMP, out), '-w', '%{http_code}|%{size_download}',
                        url], capture_output=True, text=True, timeout=timeout + 10)
    try:
        h = open(os.path.join(TEMP, out), encoding='utf-8', errors='replace').read()
    except OSError:
        h = ''
    return p.stdout.strip(), h


PAGES = [
    ('https://www.cuenca.es/webcam-plaza-mayor', 'cuen_pm.html'),
    ('https://www.cuenca.es/webcam-san-miguel', 'cuen_sm.html'),
    ('https://torrevieja.com/webcam/', 'torv_tour.html'),
    ('https://www.eltiempoentorrevieja.es/webcams-de-torrevieja', 'torv_mastral.html'),
    ('https://webcams.eltiempoentorrevieja.es/', 'torv_wcs.html'),
]
for url, out in PAGES:
    st, h = fetch(url, out)
    print('== %s -> %s (len %d)' % (url, st, len(h)))
    pats = {
        'img': r'<img[^>]+src=["\']([^"\']+)',
        'iframe': r'<iframe[^>]+src=["\']([^"\']+)',
        'm3u8': r'https?://[^"\'\s\\]+\.m3u8[^"\'\s\\]*',
        'yt': r'(?:youtube\.com/embed/|youtu\.be/|youtube\.com/live/|watch\?v=)([\w-]{11})',
        'yt-channel': r'youtube\.com/(?:channel/|@)([\w@.-]+)',
        'cam-ish': r'https?://[^"\'\s\\]*(?:cam|stream|live|mjpg|snapshot)[^"\'\s\\]*',
        'jpg': r'https?://[^"\'\s\\]+\.(?:jpg|jpeg)[^"\'\s\\]*',
    }
    for k, p in pats.items():
        m = sorted(set(re.findall(p, h, re.I)))
        if m:
            print('  %s (%d):' % (k, len(m)))
            for x in m[:14]:
                print('    ', x[:150])

print('\n--- CSV torrevieja/cuenca hits detail ---')
rows = list(csv.DictReader(open(ROOT + r'\controllable_Webcams.csv', newline='', encoding='utf-8')))
for needle in ('torrevieja', 'cuenca', 'mastral', 'eltiempoentorrevieja', 'la mata'):
    hits = [r for r in rows if needle.lower() in ' '.join(
        (r.get(k) or '') for k in ('url', 'live_stream_url', 'notes', 'project_name',
                                   'description', 'city')).lower()]
    print(' %-22s -> %d' % (needle, len(hits)))
    for h in hits[:6]:
        print('    %s | %s | %s | %s' % (h['csv_id'], (h['project_name'] or '')[:36],
                                         (h['live_stream_url'] or h['url'] or '')[:64],
                                         h['live_status']))
