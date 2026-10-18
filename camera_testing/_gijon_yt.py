import os
import re

html = open(os.environ['TEMP'] + r'\gijon_yt_streams.html', encoding='utf-8', errors='replace').read()
print('len', len(html))
ids = sorted(set(re.findall(r'"videoId":"([\w-]{11})"', html)))
print('videoIds:', len(ids))
tm = dict(re.findall(r'"videoId":"([\w-]{11})"[^}]{0,1200}?"title":\{"runs":\[\{"text":"([^"]+)"', html))
lives = sorted(set(re.findall(r'"isLive":(\w+)', html)))
print('isLive flags:', lives)
for i in ids:
    print('  %s | live=%s | %s' % (
        i,
        bool(re.search(r'"videoId":"%s"[^}]{0,2000}?"isLive":true' % re.escape(i), html)),
        tm.get(i, '?')[:90]))
