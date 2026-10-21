import re, urllib.request, ssl, time, sys

def get(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0',
        'Accept': 'text/html',
    })
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
        return r.read().decode('utf-8', 'replace')

def og_video(html):
    m = re.search(r'property="og:video" content="([^"]+)"', html)
    return m.group(1) if m else None

def og_image(html):
    m = re.search(r'property="og:image" content="([^"]+)"', html)
    return m.group(1) if m else None

cams = sys.argv[1:] or ['15045']
for cam in cams:
    url = f'https://webtvfc.feratel.com/webtv/?cam={cam}&t=1&lg=en&design=v5'
    h1 = get(url)
    v1 = og_video(h1)
    print(f'cam {cam} T0: {v1}')
    sys.stdout.flush()
    time.sleep(70)
    h2 = get(url)
    v2 = og_video(h2)
    print(f'cam {cam} T1: {v2}')
    print(f'  rotated: {v1 != v2}')
