import urllib.request, socket, re
socket.setdefaulttimeout(15)
req = urllib.request.Request('https://trafficvision.live/', headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64) AppleWebKit/537.36 Chrome/124.0'})
r = urllib.request.urlopen(req, timeout=15)
html = r.read().decode('utf-8', errors='replace')
print('total html:', len(html))
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\trafficvision_home.html', 'w') as f:
    f.write(html)
# Find all srcs
srcs = re.findall(r'src=[\"]([^\"]+)[\"]', html)
print('all srcs:')
for s in srcs[:30]:
    print(' ', s)
# Find all URLs in HTML
urls = re.findall(r'https?://[^\s\"<>]+', html)
print('all urls:')
unique = list(set(urls))
for u in unique[:40]:
    print(' ', u)
