import urllib.request, socket, re
socket.setdefaulttimeout(30)

# Get all JS files
assets = [
    'https://trafficvision.live/assets/api-CmVqwtkf.js',
    'https://trafficvision.live/assets/CollectionsContext-BtW6PfQp.js',
    'https://trafficvision.live/assets/FeedPortalContext-9FGykFYJ.js',
    'https://trafficvision.live/assets/AuthContext-Dr7IYqGd.js',
    'https://trafficvision.live/assets/AuthModal-CHApM5NO.js',
    'https://trafficvision.live/assets/useViewableRefresh-CXYzVlam.js',
    'https://trafficvision.live/assets/chunk-62JRHF6Z-qo8Ue2HG.js',
    'https://trafficvision.live/assets/PremiumContext-N0A5tk2a.js',
    'https://trafficvision.live/assets/PendingCheckoutContext-Bl9eqBvX.js',
    'https://trafficvision.live/assets/lazyPages-ByzPC0zp.js',
    'https://trafficvision.live/assets/locationHierarchy-xKRFqNDA.js',
    'https://trafficvision.live/assets/previewStatus-BpQIVnJQ.js',
    'https://trafficvision.live/assets/premiumCheckout-B3_BXULU.js',
    'https://trafficvision.live/assets/my-routes-l-C3Qdar.js',
    'https://trafficvision.live/assets/route-detail-Clz1FrWx.js',
    'https://trafficvision.live/assets/map-DtV9tvX2.js',
]

for u in assets:
    try:
        req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
        r = urllib.request.urlopen(req, timeout=20)
        js = r.read().decode('utf-8', errors='replace')
        # Look for any collection/firestore calls
        colls = set(re.findall(r'collection\([\"\']([^\"\']+)[\"\']', js))
        docs = set(re.findall(r'doc\([\"\']([^\"\']+)[\"\']', js))
        refs = re.findall(r'(?:collection|doc|document)Ref?\([\"\']([^\"\']+)[\"\']', js)
        all_colls = colls | docs | set(refs)
        if all_colls:
            print(f'\n{u.split("/")[-1]} ({len(js)} chars):')
            for c in sorted(all_colls):
                print(f'  {c}')
    except Exception as e:
        print(f'ERR {u}: {str(e)[:50]}')
