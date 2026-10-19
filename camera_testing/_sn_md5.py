import hashlib
import json
import os
import subprocess

TEMP = os.environ['TEMP']
ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
OUT = os.path.join(ROOT, 'camera_testing', '_sn_hotspot')
os.makedirs(OUT, exist_ok=True)
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
data = json.load(open(os.path.join(TEMP, 'sn_feratel_all.json'), encoding='utf-8'))

sigs = {}
for cid in data:
    for frame in ('0',):
        url = 'https://webtvhotspot.feratel.com/hotspot/37/%s/%s.jpeg?design=v3' % (cid, frame)
        p = os.path.join(OUT, 'hs_%s_%s.jpg' % (cid, frame))
        subprocess.run(['curl', '-sL', '-A', UA, '--max-time', '30', '-o', p, url],
                       capture_output=True, timeout=40)
        b = open(p, 'rb').read()
        h = hashlib.md5(b).hexdigest()
        sigs.setdefault(h, []).append((cid, frame, len(b)))

# official Pradollano
p = os.path.join(OUT, 'pradollano_snap_c1.jpg')
subprocess.run(['curl', '-sL', '-A', UA, '--max-time', '30', '-o', p,
                'https://recursos.sierranevada.es/_extras/fotos_camaras/pradollano/snap_c1.jpg'],
               capture_output=True, timeout=40)
b = open(p, 'rb').read()
h = hashlib.md5(b).hexdigest()
sigs.setdefault(h, []).append(('pradollano', 'c1', len(b)))

print('unique image bodies:', len(sigs))
for h, items in sorted(sigs.items(), key=lambda kv: -len(kv[1])):
    flag = '  <-- IDENTICAL x%d' % len(items) if len(items) > 1 else ''
    print(' %s %s%s' % (h[:12], items, flag))
