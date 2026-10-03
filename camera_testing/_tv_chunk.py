import urllib.request, socket, re
socket.setdefaulttimeout(15)
req = urllib.request.Request('https://trafficvision.live/assets/chunk-62JRHF6Z-qo8Ue2HG.js', headers={'User-Agent': 'Mozilla/5.0'})
r = urllib.request.urlopen(req, timeout=15)
js = r.read().decode('utf-8', errors='replace')
print('chunk size:', len(js))
urls = re.findall(r'"(https?://[^"]+)"', js)
print('URLs in js:', len(urls))
# Filter for data URLs
data_urls = [u for u in urls if 'data.' in u or '.json' in u]
print('data URLs:', len(data_urls))
for u in data_urls[:20]:
    print(' ', u[:200])
