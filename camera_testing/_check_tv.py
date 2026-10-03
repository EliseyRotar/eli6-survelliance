import urllib.request, socket, json
socket.setdefaulttimeout(15)
urls = [
    'https://trafficvision.live/api/cameras.json',
    'https://trafficvision.live/data/cameras.json',
    'https://trafficvision.live/static/data/cameras.json',
    'https://trafficvision.live/cameras.json',
    'https://trafficvision.live/api.json',
    'https://trafficvision.live/data.json',
    'https://trafficvision.live/_next/static/data.json',
    'https://trafficvision.live/manifest.json',
    'https://trafficvision.live/cameras.geojson',
    'https://trafficvision.live/api/cameras',
    'https://trafficvision.live/api/v1/cameras',
]
for u in urls:
    try:
        req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0'})
        r = urllib.request.urlopen(req, timeout=6)
        body = r.read()[:300].decode('utf-8', errors='replace')
        ct = r.headers.get('Content-Type', '')
        print(f'{u}: {r.status} ct={ct[:30]}')
        print(f'  {body[:200]}')
    except Exception as e:
        print(f'{u}: ERR {str(e)[:80]}')
