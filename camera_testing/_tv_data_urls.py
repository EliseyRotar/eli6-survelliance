import urllib.request, socket, re
socket.setdefaulttimeout(30)

# Get all JS files
assets = [
    'https://trafficvision.live/assets/api-CmVqwtkf.js',
    'https://trafficvision.live/assets/useViewableRefresh-CXYzVlam.js',
    'https://trafficvision.live/assets/chunk-62JRHF6Z-qo8Ue2HG.js',
    'https://trafficvision.live/assets/AuthContext-Dr7IYqGd.js',
]

# Look for ALL URLs including data.trafficvision.live
for u in assets:
    try:
        req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
        r = urllib.request.urlopen(req, timeout=30)
        js = r.read().decode('utf-8', errors='replace')
        # data.trafficvision.live URLs
        data_urls = set(re.findall(r'(https?://data\.trafficvision\.live/[^\"\']+)', js))
        # b-cdn URLs
        cdn_urls = set(re.findall(r'(https?://[^/]*b-cdn\.net/[^\"\']+)', js))
        # Other TV subdomains
        tv_urls = set(re.findall(r'(https?://[a-z0-9.-]*trafficvision\.live/[^\"\']+)', js))
        all_urls = data_urls | cdn_urls | tv_urls
        if all_urls:
            print(f'\n{u.split("/")[-1]}:')
            for u2 in sorted(all_urls):
                print(f'  {u2[:200]}')
    except Exception as e:
        print(f'ERR {u}: {str(e)[:50]}')
