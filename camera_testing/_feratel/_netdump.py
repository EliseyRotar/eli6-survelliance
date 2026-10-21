import json, os, sys, re

p = os.path.join(os.environ['TEMP'], 'wtv_net.json')
d = json.loads(open(p, 'rb').read().decode('utf-16'))
reqs = d['data']['requests']
filt = sys.argv[1] if len(sys.argv) > 1 else None
for r in reqs:
    u = r['url']
    if filt and not re.search(filt, u, re.I):
        continue
    line = f"{r['resourceType']:11} {str(r['status'])[:4]:4} {(r['mimeType'] or '')[:26]:26} {u[:190]}"
    print(line)
