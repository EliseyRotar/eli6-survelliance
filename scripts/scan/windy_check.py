import urllib.request, json, datetime
req = urllib.request.Request('https://node.windy.com/webcams/v2.0/list?nearby=52.3676,4.9041&radius=250&limit=5')
data = json.load(urllib.request.urlopen(req))
for cam in data['cams']:
    ts = cam['lastUpdate'] / 1000
    age_s = datetime.datetime.now().timestamp() - ts
    print(f"cam {cam['id']} {cam['title'][:50]}")
    print(f"  lastUpdate: {datetime.datetime.fromtimestamp(ts).isoformat()} ({age_s/60:.1f} min ago)")
    print(f"  url: {cam['images']['current'][:80]}")
