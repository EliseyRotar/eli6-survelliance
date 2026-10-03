import urllib.request, socket, re
socket.setdefaulttimeout(15)
# Get ALL the assets
req = urllib.request.Request('https://trafficvision.live/', headers={'User-Agent': 'Mozilla/5.0'})
r = urllib.request.urlopen(req, timeout=15)
html = r.read().decode('utf-8', errors='replace')
# Find all script srcs and CSS hrefs
import re
all_assets = set()
for m in re.finditer(r'(?:src|href)=["\']([^"\']+)["\']', html):
    u = m.group(1)
    if u.startswith('/') or 'trafficvision' in u:
        all_assets.add(u)
print('assets:')
for a in sorted(all_assets):
    print(' ', a)
