import urllib.request, socket, re
socket.setdefaulttimeout(15)
req = urllib.request.Request('https://trafficvision.live/blog/a-coruna-traffic-cameras', headers={'User-Agent': 'Mozilla/5.0'})
r = urllib.request.urlopen(req, timeout=15)
html = r.read().decode('utf-8', errors='replace')
scripts = re.findall(r'(?:src|href)="([^"]+\.js)"', html)
print('JS files:')
for s in scripts:
    print(' ', s)
