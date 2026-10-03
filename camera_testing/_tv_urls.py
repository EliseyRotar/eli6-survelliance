import urllib.request, socket, re
socket.setdefaulttimeout(15)
req = urllib.request.Request('https://trafficvision.live/assets/api-CmVqwtkf.js', headers={'User-Agent':'Mozilla/5.0'})
r = urllib.request.urlopen(req, timeout=15)
js = r.read().decode('utf-8', errors='replace')
print('api length:', len(js))
patterns = [
    r'fetch\("([^"]+)"',
    r'getJSON\("([^"]+)"',
    r'\.url\s*=\s*"([^"]+)"',
    r'"\s*:\s*"(https?://[^"]+\.json)',
    r'\.src\s*=\s*"(https?://[^"]+)"',
    r'data-url="(https?://[^"]+)"',
    r'\burl\s*:\s*"(https?://[^"]+)"',
]
seen = set()
for pat in patterns:
    for m in re.finditer(pat, js):
        url = m.group(1)
        if url not in seen:
            seen.add(url)
            print(pat[:30], '->', url[:200])
print('total unique URLs found:', len(seen))
