import urllib.request, json

# RIPE for "Lurano" location
url = 'https://apps.db.ripe.net/db-web-ui/fulltextsearch/select'
query = {"query": {"bool": {"must": [{"match": {"primary-key.attribute.value": "lurano"}}]}}, "size": 50}

req = urllib.request.Request(
    url,
    data=json.dumps(query).encode(),
    method='POST',
    headers={'Content-Type': 'application/json'}
)
try:
    data = json.loads(urllib.request.urlopen(req, timeout=15).read())
    hits = data.get('hits', {}).get('hits', [])
    print(f'hits: {len(hits)}')
    for h in hits[:10]:
        s = h.get('_source', {})
        # Find inetnum
        attrs = {}
        for a in s.get('attributes', []):
            attrs[a.get('name')] = a.get('value')
        if 'inetnum' in attrs or 'netname' in attrs:
            print(f'  {attrs.get("inetnum", attrs.get("primary-key", {}).get("attribute", [{}])[0].get("value"))}')
            print(f'    netname: {attrs.get("netname")}, descr: {attrs.get("descr", "")[:60]}')
            print(f'    country: {attrs.get("country")}, admin-c: {attrs.get("admin-c")}, status: {attrs.get("status")}')
except Exception as e:
    print('err:', e)
