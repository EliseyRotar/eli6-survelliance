import json
import os
import re
import subprocess

TEMP = os.environ['TEMP']
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'


def fetch(url, out=None, timeout=35):
    args = ['curl', '-sL', '-A', UA, '--max-time', str(timeout)]
    if out:
        args += ['-o', os.path.join(TEMP, out)]
    args += ['-w', '%{http_code}|%{content_type}|%{size_download}', url]
    p = subprocess.run(args, capture_output=True, timeout=timeout + 10)
    meta = p.stdout.decode('latin-1', 'replace').strip()
    body = ''
    if out:
        try:
            body = open(os.path.join(TEMP, out), encoding='utf-8', errors='replace').read()
        except OSError:
            pass
    else:
        parts = meta.rsplit('|', 3)
        body = parts[0] if len(parts) == 4 else ''
    return meta, body


print('--- Cuenca webcam host ---')
for url in ('https://webcam.cuenca.es/', 'https://webcam.cuenca.es/webcam/'):
    meta, h = fetch(url, 'cuen_host.html')
    print(' %s -> %s len=%d' % (url, meta, len(h)))
    if h:
        t = re.findall(r'<title>([^<]+)</title>', h)
        print('   title:', t)
        for pat in (r'<iframe[^>]+src=["\']([^"\']+)', r'https?://[^"\'\s]+\.(?:m3u8|jpg|jpeg)[^"\'\s]*',
                    r'axis', r'camera_file[^\s"\']*', r'alias=([\w-]+)', r'src=["\']([^"\']+\.js[^"\']*)'):
            m = sorted(set(re.findall(pat, h, re.I)))
            if m:
                print('   %s ->' % pat[:26], [x[:110] for x in m[:8]])
        print('   snippet:', re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', h))[:400])

print('\n--- Mastral img<->yt pairing (contexts) ---')
h = open(os.path.join(TEMP, 'torv_mastral.html'), encoding='utf-8', errors='replace').read()
for m in re.finditer(r'youtube\.com/live/([\w-]{11})', h):
    s = max(0, m.start() - 700)
    ctx = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', h[s:m.start()]))
    print('  %s <= …%s' % (m.group(1), ctx[-120:]))

print('\n--- new YT ids live/title ---')
for yid in ('SxXx0nFpJRo', 'kyWsLIVS4Oo', 'pKAlUXmJnDU', 'p3m2po8KcAg'):
    meta, html = fetch('https://www.youtube.com/watch?v=%s' % yid, 'yt_%s.html' % yid, 40)
    live = '"isLive":true' in html or '"isLiveContent":true' in html
    og = re.findall(r'<meta property="og:title" content="([^"]+)"', html)
    own = re.findall(r'"ownerChannelName":"([^"]+)"', html)
    print(' %s live=%s | %s | owner=%s | %s' % (yid, live, (og or ['?'])[0][:70], (own or ['?'])[0][:24], meta))

print('\n--- IPCamLive keeper ---')
meta, h = fetch('https://g0.ipcamlive.com/player/player.php?alias=keeper&disablezoombutton=1', 'keeper.html')
print(' keeper page:', meta, 'len', len(h))
if h:
    t = re.findall(r'<title>([^<]+)</title>', h)
    print('   title:', t)
    for pat in (r'https?://[^"\'\s\\]+\.m3u8[^"\'\s\\]*', r'streamurl[^,]{0,80}', r'alias[^\n]{0,60}',
                r'source\s+src=["\']([^"\']+)', r'"(https?://[^"]+)"'):
        m = sorted(set(re.findall(pat, h, re.I)))
        if m:
            print('   %s ->' % pat[:24], [x[:120] for x in m[:8]])
