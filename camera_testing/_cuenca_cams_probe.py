import os
import re
import subprocess

TEMP = os.environ['TEMP']
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'


def head(url, timeout=20):
    p = subprocess.run(['curl', '-sIL', '-A', UA, '--max-time', str(timeout), url],
                       capture_output=True, text=True, timeout=timeout + 10)
    out = [l for l in (p.stdout or '').splitlines()
           if l.startswith(('HTTP/', 'content-type', 'Content-Type', 'last-modified',
                            'Last-Modified', 'content-length', 'Content-Length', 'location'))]
    return ' | '.join(x.strip() for x in out)


sm = open(os.path.join(TEMP, 'cuen_sm.html'), encoding='utf-8', errors='replace').read()
print('--- sanmiguel page JS markers ---')
for m in re.finditer(r'var (BaseURL|File)\s*=\s*"([^"]*)"', sm):
    print(' ', m.group(1), '=', m.group(2))
for m in re.finditer(r'(live_\w+|readImage|\.jpg)', sm):
    pass
files = sorted(set(re.findall(r'[\w/]*live_\w+[\w/]*', sm, re.I)))
print(' live_* refs:', files)

print('\n--- probe readImage paths ---')
for path in (
    'https://webcam.cuenca.es/live_plazamayor/readImage.asp',
    'https://webcam.cuenca.es/live_sanmiguel/readImage.asp',
    'https://webcam.cuenca.es/live_san_miguel/readImage.asp',
    'https://webcam.cuenca.es/live_miguel/readImage.asp',
    'https://webcam.cuenca.es/live_plazamayor/image_plazamayor.jpg',
):
    print(' %s\n   %s' % (path, head(path)))

# grab one real image to confirm freshness
p = subprocess.run(['curl', '-sL', '-A', UA, '--max-time', '20', '-o',
                    os.path.join(TEMP, 'cuen_pm.jpg'), '-w', '%{http_code}|%{content_type}|%{size_download}',
                    'https://webcam.cuenca.es/live_plazamayor/readImage.asp'],
                   capture_output=True, text=True, timeout=30)
print('\n GET pm:', p.stdout)
if os.path.exists(os.path.join(TEMP, 'cuen_pm.jpg')):
    st = os.stat(os.path.join(TEMP, 'cuen_pm.jpg'))
    print('   size', st.st_size)
