import os
import re
import subprocess

TEMP = os.environ['TEMP']
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'


def fetch(url, timeout=25):
    p = subprocess.run(['curl', '-sL', '-A', UA, '--max-time', str(timeout),
                        '-w', '|%{http_code}|%{content_type}', url],
                       capture_output=True, timeout=timeout + 10)
    raw = p.stdout
    try:
        text = raw.decode('utf-8', 'replace')
    except Exception:
        text = ''
    meta = ''
    if '|' in text:
        text, meta = text.rsplit('|', 2)[0], text.rsplit('|', 2)[1:]
    return meta, text


# 1) Cuenca plaza mayor page: context around webcam markers
h = open(os.path.join(TEMP, 'cuen_pm.html'), encoding='utf-8', errors='replace').read()
for needle in ('webcamaxis', 'webcam.cuenca', 'axis', 'cmaras', 'cámaras', 'Camaras', 'CAMERA', 'camera'):
    for m in re.finditer(re.escape(needle), h, re.I):
        s = max(0, m.start() - 200)
        e = min(len(h), m.end() + 260)
        print('CUE context [%s]: %s' % (needle, re.sub(r'\s+', ' ', h[s:e])[:380]))
        print('---')

# 2) IPCamLive stream patterns for alias=keeper
print('\n--- IPCamLive keeper stream probes ---')
for url in (
    'https://g0.ipcamlive.com/playlist/keeper/index.m3u8',
    'https://g0.ipcamlive.com/stream/keeper/index.m3u8',
    'https://g0.ipcamlive.com/stream/keeper',
    'https://g0.ipcamlive.com/playlist/keeper.m3u8',
    'https://g0.ipcamlive.com/keeper/index.m3u8',
    'https://g1.ipcamlive.com/playlist/keeper/index.m3u8',
):
    meta, body = fetch(url, 12)
    print(' %s -> %s body=%r' % (url, meta, (body or '')[:60].replace('\n', '\\n')))

# 3) torrevieja.com keeper cam context + any labels
h2 = open(os.path.join(TEMP, 'torv_tour.html'), encoding='utf-8', errors='replace').read()
for m in re.finditer(r'ipcamlive', h2, re.I):
    s = max(0, m.start() - 500)
    e = min(len(h2), m.end() + 500)
    print('\nTOUR keeper ctx:', re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', h2[s:e]))[:500])
