import urllib.request, json

# Try multiple radii and center points
points = [
    (45.6700, 9.7100, 30),   # Orio al Serio airport exact
    (45.567, 9.633, 30),    # Lurano exact
    (45.567, 9.633, 50),    # Lurano 50km
    (45.667, 9.700, 15),    # Bergamo airport area
]
all_cams = {}
for lat, lon, r in points:
    url = f'https://node.windy.com/webcams/v2.0/list?nearby={lat},{lon}&radius={r}&limit=25'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        data = json.loads(urllib.request.urlopen(req, timeout=15).read())
        for c in data.get('cams', []):
            cid = c.get('id')
            if cid not in all_cams:
                all_cams[cid] = c
                print(f'  NEW [{cid}] {c.get("title","")[:50]} | ({c.get("location",{}).get("lat")}, {c.get("location",{}).get("lon")})')
    except Exception as e:
        print(f'err ({lat},{lon},{r}):', e)

print(f'\nTotal unique cams: {len(all_cams)}')
print('\nAll cams summary:')
for cid, c in all_cams.items():
    loc = c.get('location', {})
    print(f'  [{cid}] {c.get("title","")[:60]:<60} | {loc.get("city","?")}, {loc.get("country","?")} | ({loc.get("lat")}, {loc.get("lon")})')
