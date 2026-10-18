import json
import os
import re
import urllib.request

TEMP = os.environ['TEMP']
UA = {'User-Agent': 'Mozilla/5.0'}

paras = json.load(open(TEMP + r'\gijon_paras.json', encoding='utf-8'))
iframes = []
for p in paras:
    pid = p['id'][0]['value']
    for f in ('field_cuerpo_1', 'field_cuerpo_2', 'body'):
        if p.get(f):
            html = p[f][0].get('value', '')
            for src in re.findall(r'src="([^"]+)"', html):
                iframes.append((pid, src, p.get('field_titulo')))
print('iframes:')
for pid, src, t in iframes:
    print('  para %s | %s | titulo=%s' % (pid, src, json.dumps(t, ensure_ascii=False)))

# resolve camstreamer embeds -> actual youtube id (follow the redirect/iframe)
resolved = []
for pid, src, t in iframes:
    yt = None
    m = re.search(r'youtube\.com/embed/([\w-]+)', src)
    if m:
        yt = m.group(1)
    elif 'camstreamer.com/yt-embed/' in src:
        try:
            req = urllib.request.Request(src, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                html = r.read().decode('utf-8', 'replace')
            m = re.search(r'youtube\.com/embed/([\w-]+)', html)
            yt = m.group(1) if m else None
            if not yt:
                m = re.search(r'youtu\.be/([\w-]+)', html)
                yt = m.group(1) if m else None
        except Exception as e:
            print('  camstreamer err', src, e)
    resolved.append((pid, yt, src))

# oEmbed titles for all resolved ids (live cam titles = cam names)
print('\noembed:')
results = []
for pid, yt, src in resolved:
    title = status = None
    if yt:
        u = 'https://www.youtube.com/oembed?url=https://www.youtube.com/watch%%3Fv%%3D%s&format=json' % yt
        try:
            req = urllib.request.Request(u, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                oe = json.loads(r.read().decode('utf-8'))
                title = oe.get('title')
                author = oe.get('author_name')
                status = 'ok'
        except Exception as e:
            status = 'err %s' % e
        # live check: watch page isLiveBroadcast
        live = None
        try:
            req = urllib.request.Request(
                'https://www.youtube.com/watch?v=' + yt, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                html = r.read().decode('utf-8', 'replace')
            live = ('isLive":true' in html) or ('isLiveContent":true' in html)
            m = re.search(r'"ownerChannelName":"([^"]+)"', html)
            chan = m.group(1) if m else None
        except Exception as e:
            chan = 'err %s' % e
    else:
        author = chan = None
    results.append({'para': pid, 'yt': yt, 'title': title, 'author': author,
                    'live': live, 'channel': chan, 'src': src})
    print('  para=%s yt=%s live=%s | %s | ch=%s | author=%s' % (
        pid, yt, live, title, chan, author))

json.dump(results, open(TEMP + r'\gijon_cams.json', 'w'), ensure_ascii=False, indent=1)
