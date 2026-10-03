"""Try alternative URLs for missing shard."""
import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

urls = [
    'https://media.trafficvision.live/shards/cbfb074892.json',
    'https://api.trafficvision.live/internal/catalog/shards/cbfb074892.json',
    'https://cdn.trafficvision.live/shards/cbfb074892.json',
    'https://data.trafficvision.live/shards/cbfb074892.json',
]
for u in urls:
    try:
        req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://trafficvision.live/'})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            body = r.read(500)
            ct = r.headers.get('Content-Type', '')
            print(f'  {u}')
            print(f'    {r.status} {ct[:30]}')
            print(f'    body: {body[:200]}')
    except urllib.error.HTTPError as e:
        body = e.read(200)
        print(f'  {u} -> HTTP {e.code}: {body[:150]}')
    except Exception as e:
        print(f'  {u} -> {str(e)[:60]}')
