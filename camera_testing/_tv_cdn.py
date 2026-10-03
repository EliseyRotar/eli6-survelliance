import urllib.request, socket
socket.setdefaulttimeout(15)
urls = [
    'https://trafficvision-cdn.b-cdn.net/camera-data/',
    'https://trafficvision-cdn.b-cdn.net/cameras/',
    'https://trafficvision-cdn.b-cdn.net/oktraffic-cameras.json',
    'https://trafficvision-cdn.b-cdn.net/camera-data/oktraffic-cameras.json',
    'https://trafficvision-cdn.b-cdn.net/index.json',
    'https://trafficvision-cdn.b-cdn.net/manifest.json',
    'https://trafficvision-cdn.b-cdn.net/all.json',
    'https://trafficvision-cdn.b-cdn.net/list.txt',
    'https://trafficvision-cdn.b-cdn.net/sources.json',
    'https://trafficvision-cdn.b-cdn.net/cameras.json',
]
for u in urls:
    try:
        req = urllib.request.Request(u, headers={'User-Agent':'Mozilla/5.0', 'Origin':'https://trafficvision.live', 'Referer':'https://trafficvision.live/'})
        r = urllib.request.urlopen(req, timeout=6)
        body = r.read()[:300].decode('utf-8', errors='replace')
        ct = r.headers.get('Content-Type', '')
        print(f'OK {u}: {r.status} ct={ct[:30]} {body[:150]}')
    except Exception as e:
        print(f'ERR {u}: {str(e)[:80]}')
