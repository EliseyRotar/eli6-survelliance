"""Get fl511 cams with proper session - first GET page, then API."""
import urllib.request
import urllib.parse
import json
import base64
import ssl
import http.cookiejar

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), urllib.request.HTTPSHandler(context=ctx))

# Step 1: GET the page to get cookies
print('[1] GET /cctv (for session)...', flush=True)
req = urllib.request.Request('https://fl511.com/cctv', headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
})
try:
    with opener.open(req, timeout=30) as r:
        print(f'  Status: {r.status}, cookies: {len(cj)}', flush=True)
        for c in cj:
            print(f'    {c.name}={c.value[:30]}', flush=True)
except Exception as e:
    print(f'  Err: {e}', flush=True)

# Step 2: GET the API
print('\n[2] GET /List/GetData/Cameras...', flush=True)
query_b64 = 'eyJjb2x1bW5zIjpbeyJkYXRhIjpudWxsLCJuYW1lIjoiIn0seyJuYW1lIjoic29ydE9yZGVyIiwicyI6dHJ1ZX0seyJuYW1lIjoicmVnaW9uIiwicyI6dHJ1ZX0seyJuYW1lIjoiY291bnR5IiwicyI6dHJ1ZX0seyJuYW1lIjoicm9hZHdheSIsInMiOnRydWV9LHsibmFtZSI6ImRpcmVjdGlvbk9mVHJhdmVsIiwicyI6dHJ1ZX0seyJuYW1lIjoiaWQiLCJzIjp0cnVlfSx7Im5hbWUiOiJmdWxsTmFtZSIsInMiOnRydWV9LHsibmFtZSI6InR5cGUiLCJzIjp0cnVlfSx7Im5hbWUiOiJpbWFnZUlkIiwicyI6dHJ1ZX0seyJuYW1lIjoib3JpZW50YXRpb24iLCJzIjp0cnVlfSx7Im5hbWUiOiJjb21wYXNzIiwicyI6dHJ1ZX0seyJuYW1lIjoibGF0aXR1ZGUiLCJzIjp0cnVlfSx7Im5hbWUiOiJsb25naXR1ZGUiLCJzIjp0cnVlfSx7Im5hbWUiOiJpc1ZpZGVvQXZhaWxhYmxlIiwicyI6dHJ1ZX0seyJuYW1lIjoiaXNWaWRlb0FjdGl2ZSIsInMiOnRydWV9LHsibmFtZSI6InZpZGVvV2lkdGgiLCJzIjp0cnVlfSx7Im5hbWUiOiJ2aWRlb0hlaWdodCIsInMiOnRydWV9XSwib3JkZXIiOlt7ImNvbHVtbiI6InNvcnRPcmRlciIsImRpciI6ImFzYyJ9XSwic3RhYXJ0IjowLCJsZW5ndGgiOjEwMCwic2VhcmNoIjp7InZhbHVlIjoiIiwicmVnZXgiOmZhbHNlfX0='

url = f'https://fl511.com/List/GetData/Cameras?query={query_b64}'
req = urllib.request.Request(url, headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'https://fl511.com/cctv',
    'Origin': 'https://fl511.com',
})
try:
    with opener.open(req, timeout=30) as r:
        data = json.loads(r.read())
        print(f'  Total: {data.get("recordsTotal")}', flush=True)
        print(f'  Returned: {len(data.get("data", []))}', flush=True)
        for d in data.get('data', [])[:3]:
            print(f'  {d}', flush=True)
except urllib.error.HTTPError as e:
    print(f'  HTTP {e.code}: {e.read()[:500]}', flush=True)
except Exception as e:
    print(f'  Err: {e}', flush=True)
