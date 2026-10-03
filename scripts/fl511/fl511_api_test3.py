"""Test fl511 API with all browser headers."""
import urllib.request
import json
import ssl

query_b64 = 'eyJjb2x1bW5zIjpbeyJkYXRhIjpudWxsLCJuYW1lIjoiIn0seyJuYW1lIjoic29ydE9yZGVyIiwicyI6dHJ1ZX0seyJuYW1lIjoicmVnaW9uIiwicyI6dHJ1ZX0seyJuYW1lIjoiY291bnR5IiwicyI6dHJ1ZX0seyJuYW1lIjoicm9hZHdheSIsInMiOnRydWV9LHsibmFtZSI6ImRpcmVjdGlvbk9mVHJhdmVsIiwicyI6dHJ1ZX0seyJuYW1lIjoiaWQiLCJzIjp0cnVlfSx7Im5hbWUiOiJmdWxsTmFtZSIsInMiOnRydWV9LHsibmFtZSI6InR5cGUiLCJzIjp0cnVlfSx7Im5hbWUiOiJpbWFnZUlkIiwicyI6dHJ1ZX0seyJuYW1lIjoib3JpZW50YXRpb24iLCJzIjp0cnVlfSx7Im5hbWUiOiJjb21wYXNzIiwicyI6dHJ1ZX0seyJuYW1lIjoibGF0aXR1ZGUiLCJzIjp0cnVlfSx7Im5hbWUiOiJsb25naXR1ZGUiLCJzIjp0cnVlfSx7Im5hbWUiOiJpc1ZpZGVvQXZhaWxhYmxlIiwicyI6dHJ1ZX0seyJuYW1lIjoiaXNWaWRlb0FjdGl2ZSIsInMiOnRydWV9LHsibmFtZSI6InZpZGVvV2lkdGgiLCJzIjp0cnVlfSx7Im5hbWUiOiJ2aWRlb0hlaWdodCIsInMiOnRydWV9XSwib3JkZXIiOlt7ImNvbHVtbiI6InNvcnRPcmRlciIsImRpciI6ImFzYyJ9XSwic3RhYXJ0IjowLCJsZW5ndGgiOjEwMCwic2VhcmNoIjp7InZhbHVlIjoiIiwicmVnZXgiOmZhbHNlfX0='

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
url = f'https://fl511.com/List/GetData/Cameras?query={query_b64}'
req = urllib.request.Request(url, headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'https://fl511.com/cctv',
    'Origin': 'https://fl511.com',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Dest': 'empty',
    'Accept-Language': 'en-US,en;q=0.9',
})
try:
    with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
        data = json.loads(r.read())
        print(f'Total: {data.get("recordsTotal")}')
        print(f'Filtered: {data.get("recordsFiltered")}')
        print(f'Returned: {len(data.get("data", []))}')
        for d in data.get('data', [])[:3]:
            print(d)
except urllib.error.HTTPError as e:
    print(f'HTTP {e.code}: {e.read()[:300]}')
except Exception as e:
    print(f'Err: {e}')
