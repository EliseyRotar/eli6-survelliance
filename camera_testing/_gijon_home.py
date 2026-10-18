import os
import re
import subprocess

TEMP = os.environ['TEMP']
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'

for tab in ('featured', 'videos'):
    p = subprocess.run(['curl', '-sL', '-A', UA, '--max-time', '40', '-o',
                        TEMP + r'\gijon_ch_%s.html' % tab, '-w', '%{http_code}',
                        'https://www.youtube.com/channel/UCGUbYgA8GKjBLZL_nujT7Xw/%s' % tab],
                       capture_output=True, text=True, timeout=60)
    html = open(TEMP + r'\gijon_ch_%s.html' % tab, encoding='utf-8', errors='replace').read()
    ids = []
    for i in re.findall(r'"videoId":"([\w-]{11})"', html):
        if i not in ids:
            ids.append(i)
    live_ids = [i for i in ids if re.search(
        r'"videoId":"%s"[^}]{0,3500}?"isLive":true' % re.escape(i), html)]
    print('%s: http=%s ids=%d live=%s' % (tab, p.stdout, len(ids), live_ids))
