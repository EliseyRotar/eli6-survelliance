import urllib.request, socket, re, json
socket.setdefaulttimeout(15)
req = urllib.request.Request('https://trafficvision.live/', headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0'})
r = urllib.request.urlopen(req, timeout=15)
html = r.read().decode('utf-8', errors='replace')
print('total html:', len(html))
# Find script srcs
script_srcs = re.findall(r'src=\"([^\"]+\.js)', html)
print('script srcs:')
for s in script_srcs[:15]:
    print(' ', s)
# Find data refs
data_refs = re.findall(r'(?:src|href|data-src|data-url)=\"(https?://[^\"]+\.(?:json|geojson|csv|js)[^\"]*)', html, re.I)
print('data refs:')
for d in data_refs[:20]:
    print(' ', d)
# Find __NEXT_DATA__
nd = re.search(r'<script[^>]*id=\"__NEXT_DATA__\"[^>]*>([^<]+)</script>', html)
if nd:
    print('__NEXT_DATA__ length:', len(nd.group(1)))
    try:
        d = json.loads(nd.group(1))
        print('__NEXT_DATA__ keys:', list(d.keys()))
        print(json.dumps(d, indent=2)[:3000])
    except Exception as e:
        print('parse err:', e)
        print(nd.group(1)[:1500])
else:
    print('no __NEXT_DATA__')
