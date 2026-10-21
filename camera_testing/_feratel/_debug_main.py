import re, json, html, sys
sys.path.insert(0, 'camera_testing\\_feratel')
from _enumerate import fetch

url = 'https://www.feratel.com/en/webcams/andorra/encamp/encamp-cortals-15090'
raw = fetch(url)
props_list = re.findall(r'<astro-island[^>]*?props="([^"]+)"', raw)
print('islands:', len(props_list))
for i, p in enumerate(props_list[:8]):
    try:
        obj = json.loads(html.unescape(p))
    except Exception as e:
        print(i, 'fail', e); continue
    keys = list(obj.keys())
    print(f'--- island {i} keys={keys}')
    if 'cam' in obj:
        print('    cam prop:', json.dumps(obj['cam'], ensure_ascii=False)[:1500])

# also dump any <script type="application/json"> or data-props
for m in re.finditer(r'<script type="application/json"[^>]*>(.*?)</script>', raw, re.S):
    s = m.group(1)
    if 'cam' in s or '15090' in s:
        print('JSONSCRIPT:', s[:800])
# find 15090 in any &quot;camId&quot; or cam= context
for m in list(re.finditer(r'cam(?:Id)?[&"]*[:=]', raw)):
    pass
hits = [m.start() for m in re.finditer('15090', raw)]
print('15090 total hits:', len(hits))
# islands containing raw '15090'
for i, p in enumerate(props_list):
    if '15090' in html.unescape(p):
        print(f'island {i} contains 15090:', html.unescape(p)[:600])
