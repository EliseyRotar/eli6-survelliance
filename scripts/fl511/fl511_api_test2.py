"""Try the exact query format from the fl511 page request."""
import urllib.request
import urllib.parse
import json
import base64
import time


# The actual query from the page network log
query_b64 = 'eyJjb2x1bW5zIjpbeyJkYXRhIjpudWxsLCJuYW1lIjoiIn0seyJuYW1lIjoic29ydE9yZGVyIiwicyI6dHJ1ZX0seyJuYW1lIjoicmVnaW9uIiwicyI6dHJ1ZX0seyJuYW1lIjoiY291bnR5IiwicyI6dHJ1ZX0seyJuYW1lIjoicm9hZHdheSIsInMiOnRydWV9LHsibmFtZSI6ImRpcmVjdGlvbk9mVHJhdmVsIiwicyI6dHJ1ZX0seyJuYW1lIjoiaWQiLCJzIjp0cnVlfSx7Im5hbWUiOiJmdWxsTmFtZSIsInMiOnRydWV9LHsibmFtZSI6InR5cGUiLCJzIjp0cnVlfSx7Im5hbWUiOiJpbWFnZUlkIiwicyI6dHJ1ZX0seyJuYW1lIjoib3JpZW50YXRpb24iLCJzIjp0cnVlfSx7Im5hbWUiOiJjb21wYXNzIiwicyI6dHJ1ZX0seyJuYW1lIjoibGF0aXR1ZGUiLCJzIjp0cnVlfSx7Im5hbWUiOiJsb25naXR1ZGUiLCJzIjp0cnVlfSx7Im5hbWUiOiJpc1ZpZGVvQXZhaWxhYmxlIiwicyI6dHJ1ZX0seyJuYW1lIjoiaXNWaWRlb0FjdGl2ZSIsInMiOnRydWV9LHsibmFtZSI6InZpZGVvV2lkdGgiLCJzIjp0cnVlfSx7Im5hbWUiOiJ2aWRlb0hlaWdodCIsInMiOnRydWV9XSwib3JkZXIiOlt7ImNvbHVtbiI6InNvcnRPcmRlciIsImRpciI6ImFzYyJ9XSwic3RhcnQiOjAsImxlbmd0aCI6MTAwLCJzZWFyY2giOnsidmFsdWUiOiIiLCJyZWdleCI6ZmFsc2V9fQ=='

decoded = base64.b64decode(query_b64).decode()
print('Decoded query:')
print(decoded[:2000])

# Try the request as-is
url = f'https://fl511.com/List/GetData/Cameras?query={urllib.parse.quote(query_b64)}'
print(f'\nURL: {url[:200]}')

req = urllib.request.Request(url, headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'https://fl511.com/cctv',
    'Origin': 'https://fl511.com',
})

try:
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read()
        print(f'\nStatus: {r.status}, Type: {r.headers.get("Content-Type", "")}')
        data = json.loads(body)
        print(f'Keys: {list(data.keys())}')
        print(f'recordsTotal: {data.get("recordsTotal", "?")}')
        print(f'recordsFiltered: {data.get("recordsFiltered", "?")}')
        print(f'Data count: {len(data.get("data", []))}')
        if data.get('data'):
            print(f'\nFirst record:')
            for k, v in data['data'][0].items():
                print(f'  {k}: {v}')
            print(f'\nSample 2nd:')
            for k, v in data['data'][1].items() if len(data['data']) > 1 else []:
                print(f'  {k}: {v}')
except urllib.error.HTTPError as e:
    print(f'\nHTTP Error: {e.code}')
    body = e.read()
    print(f'Body: {body[:2000].decode("utf-8", errors="replace")}')
except Exception as e:
    print(f'Err: {e}')
