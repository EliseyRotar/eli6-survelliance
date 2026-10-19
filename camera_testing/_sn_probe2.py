import os
import re
import subprocess

TEMP = os.environ['TEMP']
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'


def probe(url, out_name, timeout=30):
    p = subprocess.run(['curl', '-sL', '-r', '0-2048', '-A', UA, '--max-time', str(timeout),
                        '-o', os.path.join(TEMP, out_name), '-w', '%{http_code}|%{content_type}|%{size_download}',
                        url], capture_output=True, text=True, timeout=timeout + 10)
    return p.stdout.strip()


print('--- trafficvision mirrors (GET range) ---')
for cid in (15110, 15112, 15111, 15113, 15114):
    r = probe('https://media.trafficvision.live/feratel/%d.mp4' % cid, 'tv_%d.bin' % cid)
    print('  %d -> %s' % (cid, r))

print('--- hotspot/thmb (GET range) ---')
for cid in (15110, 15111, 15112, 15113, 15114):
    r = probe('https://webtvhotspot.feratel.com/hotspot/37/%d/0.jpeg?design=v3' % cid, 'hs_%d.jpg' % cid)
    print('  hs %d -> %s' % (cid, r))

print('--- webtv titles+coords (cam=...) ---')
for cid in (15110, 15111, 15112, 15113, 15114):
    out = 'webtv_%d.html' % cid
    st = probe('https://webtv.feratel.com/webtv/?design=v5&cam=%d&c1=0' % cid, out, 35)
    try:
        w = open(os.path.join(TEMP, out), encoding='utf-8', errors='replace').read()
    except OSError:
        w = ''
    t = re.findall(r'<title>([^<]+)</title>', w)
    lat = re.findall(r'infolat[^\d]*([\d.]+)', w)
    lon = re.findall(r'infolong[^\d-]*(-?[\d.]+)', w)
    print('  %d %s | title=%s | lat=%s lon=%s' % (cid, st, t[0][:90] if t else '?', lat[:2], lon[:2]))
