"""Query fl511 cameras list API to get all 4,871 cams with IDs.

API: GET /List/GetData/Cameras?query=<base64 JSON>
The query param is base64(JSON) like:
{"columns":[{"data":null,"name":""},{"name":"sortOrder","s":true},{"name":"region","s":true},...]}
"""
import urllib.request
import json
import base64
import time

def fetch_cams(start=0, length=100, region=None, county=None, search=None):
    """Fetch one page of cameras."""
    cols = [
        {"data": None, "name": ""},
        {"name": "sortOrder", "s": True},
        {"name": "region", "s": True},
        {"name": "county", "s": True},
        {"name": "roadway", "s": True},
        {"name": "directionOfTravel", "s": True},
        {"name": "id", "s": True},
        {"name": "fullName", "s": True},
        {"name": "type", "s": True},
        {"name": "imageId", "s": True},
        {"name": "orientation", "s": True},
        {"name": "compass", "s": True},
        {"name": "latitude", "s": True},
        {"name": "longitude", "s": True},
        {"name": "isVideoAvailable", "s": True},
        {"name": "isVideoActive", "s": True},
        {"name": "videoWidth", "s": True},
        {"name": "videoHeight", "s": True},
    ]
    q = {
        "columns": cols,
        "order": [{"column": "sortOrder", "dir": "asc"}],
        "start": start,
        "length": length,
        "search": {"value": search or "", "regex": False},
    }
    if region:
        # Add region filter (need to find the column index)
        # Region is the second column index 1
        q["columns"][2]["search"] = {"value": region, "regex": False}
    encoded = base64.b64encode(json.dumps(q).encode()).decode()
    url = f'https://fl511.com/List/GetData/Cameras?query={urllib.parse.quote(encoded)}'
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0',
        'X-Requested-With': 'XMLHttpRequest',
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
            return data
    except Exception as e:
        return {'error': str(e)[:200]}


import urllib.parse

# Try first 100
print('[TEST] Fetching first 100 cams...', flush=True)
data = fetch_cams(start=0, length=10)
if 'error' in data:
    print(f'Error: {data["error"]}', flush=True)
else:
    print(f'Keys: {list(data.keys())}', flush=True)
    print(f'recordsTotal: {data.get("recordsTotal", "?")}', flush=True)
    print(f'recordsFiltered: {data.get("recordsFiltered", "?")}', flush=True)
    print(f'Number of records: {len(data.get("data", []))}', flush=True)
    if data.get('data'):
        print('\nFirst record keys:', list(data['data'][0].keys()) if isinstance(data['data'][0], dict) else 'not dict')
        print('First record:', data['data'][0])
        print('\nSample 2nd:', data['data'][1] if len(data['data']) > 1 else 'none')
