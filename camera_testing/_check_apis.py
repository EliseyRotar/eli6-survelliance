import urllib.request, socket
socket.setdefaulttimeout(10)
apis = [
    'https://earthcam.com/api/v1/cameras',
    'https://www.chart.state.md.us/feeds/Json/Cameras.json',
    'https://www.deldot.gov/listData/CCTV/',
    'https://web6.seattle.gov/Traveler/api/Video/Cameras',
    'https://api.511.org/cameras/list?api_key=',
    'https://geoservices.tamu.edu/Bus/Routes/v1/Cameras',
    'https://services.arcgis.com/cJ9YHowT8TU7DUyn/arcgis/rest/services/Camera/FeatureServer/0/query',
]
for u in apis:
    try:
        req = urllib.request.Request(u, headers={'User-Agent':'Mozilla/5.0'})
        r = urllib.request.urlopen(req, timeout=6)
        ct = r.headers.get('Content-Type', '')
        body = r.read()[:300].decode('utf-8', errors='replace')
        print(f'{u[:60]}: {r.status} ct={ct[:30]} len={len(body)}')
    except Exception as e:
        print(f'{u[:60]}: ERR {str(e)[:60]}')
