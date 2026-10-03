"""Check cam 615 in trace."""
import json

with open('fl511_full_trace.json') as f:
    data = json.load(f)
for r in data:
    if '615' in str(r.get('url', '')):
        if 'response' in r:
            print(f'[{r["response"]["status"]}] {r.get("url", "")[:200]}')
        else:
            print(f'[{r.get("method")}] {r.get("url", "")[:200]}')
            if r.get('post_data'):
                print(f'    body: {r["post_data"][:300]}')
            h = r.get('headers', {})
            for k in h:
                if 'token' in k.lower() or 'auth' in k.lower() or 'cookie' in k.lower():
                    print(f'    {k}: {h[k][:200]}')
