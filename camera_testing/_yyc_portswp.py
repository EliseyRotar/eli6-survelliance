# -*- coding: utf-8 -*-
"""Session 48: cam-host port/path sweep (live-feed hunt last pass)."""
import json
import os
import subprocess

TEMP = os.environ['TEMP']
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'


def get(url, timeout=12, out='sw.bin'):
    op = os.path.join(TEMP, out)
    p = subprocess.run(['curl', '-sL', '-A', UA, '--max-time', str(timeout),
                        '-o', op, '-w', '%{http_code}|%{content_type}|%{size_download}',
                        url], capture_output=True, text=True, timeout=timeout + 8)
    prev = b''
    if os.path.exists(op):
        with open(op, 'rb') as f:
            prev = f.read(100)
    return p.stdout.strip(), prev


# InternetDB on cam host
for ip in ('198.160.191.75',):
    try:
        p = subprocess.run(['curl', '-s', '--max-time', '15',
                            'https://internetdb.shodan.io/%s' % ip],
                           capture_output=True, text=True, timeout=20)
        d = json.loads(p.stdout)
        print('InternetDB %s: ports=%s' % (ip, d.get('ports')))
    except Exception as e:
        print('InternetDB fail:', e)

# alt ports + paths on trafficcam host
probes = [
    'http://trafficcam.calgary.ca:8080/loc86.jpg',
    'http://trafficcam.calgary.ca:8000/loc86.jpg',
    'http://trafficcam.calgary.ca:554/loc86.jpg',
    'https://trafficcam.calgary.ca:8443/loc86.jpg',
    'https://trafficcam.calgary.ca/admin/',
    'https://trafficcam.calgary.ca/status',
    'https://trafficcam.calgary.ca/axis-cgi/jpg/image.cgi',
    'https://trafficcam.calgary.ca/ISAPI/Streaming/channels/101/picture',
    'https://trafficcam.calgary.ca/video',
    'https://trafficcam.calgary.ca/loc86',
    'https://trafficcam.calgary.ca/getimage.cgi?id=86',
    'https://trafficcam.calgary.ca/image?cam=86',
    'https://trafficcam.calgary.ca/web/?id=86',
    'https://atis.calgary.ca/',
    'https://www.calgary.ca/roads/conditions/atis.html',
]
for u in probes:
    meta, prev = get(u)
    code = meta.split('|')[0]
    if code not in ('404', '000'):
        print(' %-76s -> %s %r' % (u[:76], meta, prev[:50]))
print('done (only non-404 printed)')
