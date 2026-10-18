import os
import re
import subprocess

TEMP = os.environ['TEMP']
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
p = subprocess.run(['curl', '-sL', '-A', UA, '--max-time', '40', '-o',
                    TEMP + r'\gijon_ch_streams.html', '-w', '%{http_code}|%{size_download}',
                    'https://www.youtube.com/channel/UCGUbYgA8GKjBLZL_nujT7Xw/streams'],
                   capture_output=True, text=True, timeout=60)
print('streams page:', p.stdout)

html = open(TEMP + r'\gijon_ch_streams.html', encoding='utf-8', errors='replace').read()
print('len', len(html))
ids = re.findall(r'"videoId":"([\w-]{11})"', html)
seen = []
for i in ids:
    if i not in seen:
        seen.append(i)
print('unique videoIds:', len(seen))
tm = dict(re.findall(r'"videoId":"([\w-]{11})"[^}]{0,1500}?"title":\{"runs":\[\{"text":"([^"]+)"', html))
known = {'ncuuM-iMl3A', 'arVrUGnJRlc', 'hAweouDR-vM', 'e3TFH0g1mvU'}
for i in seen:
    is_live = bool(re.search(r'"videoId":"%s"[^}]{0,3000}?"isLive":true' % re.escape(i), html))
    print('  %s live=%-5s %s %s' % (i, is_live, '<- KNOWN' if i in known else '', tm.get(i, '?')[:80]))
