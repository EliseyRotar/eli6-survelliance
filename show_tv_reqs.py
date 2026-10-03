"""Show TV requests."""
import json
from urllib.parse import urlparse

with open('tv_api_capture.json') as f:
    reqs = json.load(f)
print(f'Total: {len(reqs)} requests')
domains = set()
for r in reqs:
    u = urlparse(r['url'])
    domains.add(u.netloc)
print(f'Domains: {sorted(domains)}')
# Show non-google/non-cdn
for r in reqs:
    if 'googleapis' not in r['url'] and 'gstatic' not in r['url'] and 'cloudflare' not in r['url'] and 'w3.org' not in r['url'] and 'twitter' not in r['url'] and 'facebook' not in r['url'] and 'youtube' not in r['url']:
        method = r['method']
        url = r['url'][:200]
        print(f'  [{method}] {url}')
