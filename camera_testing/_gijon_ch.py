import os
import re
import subprocess
import json

TEMP = os.environ['TEMP']
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
p = subprocess.run(['curl', '-sL', '-A', UA, '--max-time', '40', '-o',
                    TEMP + r'\gijon_watch.html', '-w', '%{http_code}|%{size_download}',
                    'https://www.youtube.com/watch?v=ncuuM-iMl3A'],
                   capture_output=True, text=True, timeout=60)
print('watch:', p.stdout)

html = open(TEMP + r'\gijon_watch.html', encoding='utf-8', errors='replace').read()
print('len', len(html))
for pat in (r'"channelId":"(UC[\w-]{22})"', r'"externalId":"(UC[\w-]{22})"',
            r'"vanityChannelUrl":"([^"]+)"', r'"canonicalBaseUrl":"/@([^"]+)"',
            r'"/channel/(UC[\w-]{22})"'):
    print(pat[:40], '->', sorted(set(re.findall(pat, html)))[:8])
print('isLiveBroadcast:', 'isLiveBroadcast' in html)
m = re.search(r'"title":"([^"]+)"[^}]{0,400}?"ownerChannelName":"([^"]+)"', html)
print('title/owner:', m.groups() if m else '?')
