import urllib.request, json
req = urllib.request.Request('https://node.windy.com/webcams/v2.0/list?nearby=52.3676,4.9041&radius=250&limit=2')
data = json.load(urllib.request.urlopen(req))
for cam in data['cams']:
    print(json.dumps(cam, indent=2))
    print()
    print("===")
