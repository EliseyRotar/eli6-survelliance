# -*- coding: utf-8 -*-
"""Session 48: Calgary traffic cams recon.

- Socrata: k7p9-kppz (Traffic Cameras), y47k-7e97 (Locations), dv2f-necx (safety)
- trafficcam.calgary.ca image host: probe video/mjpg variants
- calgary.ca main page: any extra cams/lists
- trafficcalgary.ca aggregator: extra sources (AB 511?)
"""
import json
import os
import subprocess
import tempfile

TEMP = os.environ['TEMP']
ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'


def fetch(url, out=None, timeout=60, extra=None):
    args = ['curl', '-sL', '-A', UA, '--max-time', str(timeout)]
    if extra:
        args += extra
    if out:
        args += ['-o', os.path.join(TEMP, out)]
    args += ['-w', '%{http_code}|%{content_type}|%{size_download}', url]
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout + 15)
    body = ''
    if out:
        try:
            body = open(os.path.join(TEMP, out), encoding='utf-8', errors='replace').read()
        except OSError:
            pass
    return p.stdout.strip(), body


# 1) Socrata traffic cameras (full dump)
for dsid, name in (('k7p9-kppz', 'cams'), ('y47k-7e97', 'locs'), ('dv2f-necx', 'safety')):
    meta, _ = fetch('https://data.calgary.ca/resource/%s.json?$limit=5000' % dsid,
                    out='%s.json' % dsid, timeout=90)
    print('socrata %s (%s): %s' % (dsid, name, meta))
    try:
        d = json.load(open(os.path.join(TEMP, '%s.json' % dsid), encoding='utf-8'))
        print('  rows:', len(d))
        if d:
            print('  keys:', sorted(d[0].keys()))
            print('  sample:', json.dumps(d[0], ensure_ascii=False)[:500])
    except Exception as e:
        print('  parse fail:', e)

# 2) trafficcam.calgary.ca root + live variants
print('\n--- trafficcam.calgary.ca variants ---')
probe_ids = [1, 2, 17, 100, 200, 300, 400, 500]
for i in probe_ids:
    url = 'https://trafficcam.calgary.ca/loc%d.jpg' % i
    meta, _ = fetch(url, timeout=15)
    print(' loc%d.jpg -> %s' % (i, meta))
for path in ('/', '/index.html', '/map', '/cameras', '/live', '/stream', '/video',
             '/loc1.m3u8', '/loc1.mjpg', '/loc1.mjpeg', '/loc1/index.m3u8',
             '/hls/loc1/index.m3u8', '/stream/loc1', '/axis-cgi/mjpg/video.cgi',
             '/video.mjpg', '/cam.mjpg'):
    meta, body = fetch('https://trafficcam.calgary.ca%s' % path, timeout=12,
                       out=None)
    print(' %-28s -> %s %r' % (path, meta, (body or '')[:80].replace('\n', ' ')))

# 3) calgary.ca main cam page
meta, h = fetch('https://www.calgary.ca/roads/conditions/traffic-cameras.html',
                out='calgary_cams.html', timeout=45)
print('\ncalgary.ca page:', meta, 'len', len(h))

# 4) trafficcalgary.ca aggregator
meta, h2 = fetch('https://trafficcalgary.ca/', out='tcagary.html', timeout=45)
print('trafficcalgary.ca:', meta, 'len', len(h2))
