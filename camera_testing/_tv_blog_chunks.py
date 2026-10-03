import urllib.request, socket, re
socket.setdefaulttimeout(15)
url = 'https://trafficvision.live/blog/a-coruna-traffic-cameras'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html'})
r = urllib.request.urlopen(req, timeout=15)
html = r.read().decode('utf-8', errors='replace')
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\_blog_a_coruna.html', 'w', encoding='utf-8') as f:
    f.write(html)
chunks = re.findall(r'"(/assets/[^"]+\.js)"', html)
print('chunks:')
for c in chunks:
    print(' ', c)
