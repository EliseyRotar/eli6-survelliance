import urllib.request, socket
socket.setdefaulttimeout(15)
urls = [
    'https://trafficvision.live/cam/oktraffic-video-1103130967',
    'https://trafficvision.live/camera/oktraffic-video-1103130967',
    'https://trafficvision.live/cameras/oktraffic-video-1103130967',
    'https://trafficvision.live/api/v1/cameras/oktraffic-video-1103130967',
    'https://trafficvision.live/v1/cameras/oktraffic-video-1103130967',
    'https://trafficvision.live/feed/oktraffic-video-1103130967',
    'https://trafficvision.live/cam?id=oktraffic-video-1103130967',
]
for u in urls:
    try:
        req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
        r = urllib.request.urlopen(req, timeout=6)
        body = r.read()[:200].decode('utf-8', errors='replace')
        ct = r.headers.get('Content-Type', '')
        print(f'{u}: {r.status} ct={ct[:30]}')
        print(f'  body: {body[:150]}')
    except Exception as e:
        print(f'{u}: {str(e)[:80]}')
