import urllib.request, socket, re
socket.setdefaulttimeout(15)
req = urllib.request.Request('https://trafficvision.live/assets/useViewableRefresh-CXYzVlam.js', headers={'User-Agent': 'Mozilla/5.0'})
r = urllib.request.urlopen(req, timeout=15)
js = r.read().decode('utf-8', errors='replace')
print('useViewableRefresh size:', len(js))
urls = re.findall(r'"(https?://[^"]+)"', js)
print('URLs in js:', len(urls))
for u in urls[:20]:
    print(' ', u[:200])
