import os
import re
import subprocess

TEMP = os.environ['TEMP']
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'

h = open(os.path.join(TEMP, 'cuen_sm2.html'), encoding='utf-8', errors='replace').read()
for needle in ('imagen.php', 'image-r'):
    for m in re.finditer(re.escape(needle), h, re.I):
        s = max(0, m.start() - 450)
        e = min(len(h), m.end() + 450)
        print('CTX [%s]:\n%s\n---' % (needle, re.sub(r'\s+', ' ', h[s:e])[:700]))


def head(url, timeout=20):
    p = subprocess.run(['curl', '-sIL', '-A', UA, '--max-time', str(timeout), url],
                       capture_output=True, text=True, timeout=timeout + 10)
    out = [l for l in (p.stdout or '').splitlines()
           if l.startswith(('HTTP/', 'Content-Type', 'Last-Modified', 'Content-Length', 'location'))]
    return ' | '.join(x.strip() for x in out)


print('\n--- probes ---')
for url in (
    'https://cuenca.es/webcam/imagen.php',
    'https://cuenca.es/webcam/image-r.jpg',
    'https://cuenca.es/webcam/image.jpg',
    'https://www.cuenca.es/webcam/imagen.php',
):
    print(' %s\n   %s' % (url, head(url)))

# freshness: pull imagen.php twice, 6s apart, compare last-modified/size
import hashlib
for label, u in (('imagen.php', 'https://cuenca.es/webcam/imagen.php'),
                 ('pm-readImage', 'https://webcam.cuenca.es/live_plazamayor/readImage.asp')):
    digests = []
    for i in range(2):
        p = subprocess.run(['curl', '-sL', '-A', UA, '--max-time', '20', '-o',
                            os.path.join(TEMP, 'fresh.bin'), '-w', '%{http_code}|%{content_type}|%{size_download}',
                            u], capture_output=True, text=True, timeout=30)
        try:
            body = open(os.path.join(TEMP, 'fresh.bin'), 'rb').read()
        except OSError:
            body = b''
        digests.append((p.stdout.strip(), hashlib.md5(body).hexdigest()[:10]))
        if i == 0:
            import time
            time.sleep(6)
    print(' freshness %-12s %s' % (label, digests))
