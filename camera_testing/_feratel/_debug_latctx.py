import re, json, sys
sys.path.insert(0, 'camera_testing\\_feratel')
from _enumerate import fetch

url = 'https://www.feratel.com/en/webcams/austria/lower-austria/hardegg-nationalpark-thayatal-5080'
raw = fetch(url)
for m in list(re.finditer('latitude', raw))[:6]:
    s = max(0, m.start() - 350)
    print('--- ctx:', raw[s:m.start() + 250].replace('\n', ' '))
    print()
# uuid context - what references it
uu = '8245bd4a-549c-403f-9120-36b31085ebb0'
for m in list(re.finditer(uu, raw))[:5]:
    s = max(0, m.start() - 250)
    print('UUID ctx:', raw[s:m.start() + 150].replace('\n', ' ')[:400])
    print()
# find any endpoint/api calls in inline scripts
for m in list(re.finditer(r'(endpointId|/api/|fetch\()', raw))[:10]:
    s = max(0, m.start() - 100)
    print('API ctx:', raw[s:m.start() + 200].replace('\n', ' ')[:300])
