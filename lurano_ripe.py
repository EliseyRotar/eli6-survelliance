import urllib.request, json

# Try RIPE search for Lurano
urls = [
    'https://rest.db.ripe.net/search.json?query-string=lurano&type-filter=inetnum&flags=no-referenced',
    'https://rest.db.ripe.net/search.json?query-string=lurano&type-filter=inetnum',
    'https://rest.db.ripe.net/search.json?query-string=lurano+IT&type-filter=inetnum',
]
for url in urls:
    try:
        req = urllib.request.Request(url, headers={'Accept': 'application/json'})
        data = json.loads(urllib.request.urlopen(req, timeout=15).read())
        objs = data.get('objects', {}).get('object', [])
        if objs:
            print(f'URL: {url}')
            print(f'  found {len(objs)} objects')
            for o in objs[:5]:
                for a in o.get('attributes', {}).get('attribute', []):
                    if a.get('name') in ('inetnum', 'netname', 'descr', 'country'):
                        print(f'    {a.get("name")}: {a.get("value")[:80]}')
            break
    except Exception as e:
        print(f'err {url}: {e}')
