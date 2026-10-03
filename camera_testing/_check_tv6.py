import urllib.request, socket, re
socket.setdefaulttimeout(15)
for js in ['/assets/firebase-vendor-zv39oyyy.js', '/assets/firebase-CvumGE-S.js', '/assets/api-CmVqwtkf.js']:
    url = 'https://trafficvision.live' + js
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        r = urllib.request.urlopen(req, timeout=10)
        js_text = r.read().decode('utf-8', errors='replace')
        print('=== {} ({}) ==='.format(js, len(js_text)))
        patterns = [
            r'projectId["\',\s]+["\']([^"\']+)',
            r'apiKey["\',\s]+["\']([^"\']+)',
            r'databaseURL["\',\s]+["\']([^"\']+)',
            r'collection\(["\']([^"\']+)',
            r'firestore\.googleapis\.com/v1/projects/([^"\']+)',
        ]
        for pat in patterns:
            for m in re.finditer(pat, js_text):
                print(' ', m.group(0)[:150])
    except Exception as e:
        print('{} ERR {}'.format(js, str(e)[:60]))
