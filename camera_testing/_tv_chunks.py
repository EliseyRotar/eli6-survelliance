import urllib.request, socket, re
socket.setdefaulttimeout(15)
urls = [
    'https://trafficvision.live/assets/home-BhN5Yvie.js',
    'https://trafficvision.live/assets/lazyPages-ByzPC0zp.js',
    'https://trafficvision.live/assets/locationHierarchy-xKRFqNDA.js',
    'https://trafficvision.live/assets/previewStatus-BpQIVnJQ.js',
    'https://trafficvision.live/assets/useViewableRefresh-CXYzVlam.js',
    'https://trafficvision.live/assets/chunk-62JRHF6Z-qo8Ue2HG.js',
]
for u in urls:
    try:
        req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
        r = urllib.request.urlopen(req, timeout=15)
        body = r.read().decode('utf-8', errors='replace')
        urls_in = re.findall(r'"(https?://[^"]+\.json)"', body)
        print(f'{u}: {len(body)} chars, json URLs: {len(urls_in)}')
        for x in urls_in[:5]:
            print(f'  {x[:200]}')
    except Exception as e:
        print(f'ERR {u}: {str(e)[:60]}')
