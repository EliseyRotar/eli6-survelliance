import urllib.request, json
url = 'https://node.windy.com/webcams/v2.0/list?nearby=45.6700,9.7100&radius=15&limit=25'
req = urllib.request.Request(url, headers={
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0',
    'Accept': 'application/json',
})
try:
    data = json.loads(urllib.request.urlopen(req, timeout=15).read())
    cams = data.get('cams', [])
    print(f'Windy cams within 15km of Orio al Serio: {len(cams)}')
    for c in cams[:30]:
        loc = c.get('location', {})
        title = c.get('title', '')
        cid = c.get('id')
        print(f'  [{cid}] {title[:55]}')
        print(f'    ({loc.get("lat")}, {loc.get("lon")})')
        urls = c.get('urls', {})
        for k, v in urls.items():
            print(f'    {k}: {v[:80]}')
except Exception as e:
    print('err:', e)
