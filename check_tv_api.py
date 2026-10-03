"""Check TV API endpoints."""
import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

urls = [
    'https://api.trafficvision.live/v1/cameras',
    'https://api.trafficvision.live/cameras',
    'https://api.trafficvision.live/v1/cameras?limit=10',
    'https://api.trafficvision.live/v2/cameras',
    'https://node.trafficvision.live/v1/cameras',
    'https://api.trafficvision.live/v1/streams',
    'https://api.trafficvision.live/v1/sources',
]
for u in urls:
    try:
        req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
            body = r.read(200)
            print(f'  {u} -> {r.status} {r.headers.get("Content-Type", "")[:30]} ({len(body)} preview)')
    except urllib.error.HTTPError as e:
        print(f'  {u} -> HTTP {e.code}')
    except Exception as e:
        print(f'  {u} -> {str(e)[:60]}')
