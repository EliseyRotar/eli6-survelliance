import re, json, html, sys
sys.path.insert(0, 'camera_testing\\_feratel')
from _enumerate import fetch

url = 'https://www.feratel.com/en/webcams/austria/lower-austria/hardegg-nationalpark-thayatal-5080'
raw = fetch(url)
islands = []
for pm in re.finditer(r'<astro-island[^>]*?props="([^"]+)"', raw):
    try:
        islands.append(json.loads(html.unescape(pm.group(1))))
    except Exception as e:
        islands.append({'_fail': str(e)})
print('islands:', len(islands))
for i, obj in enumerate(islands):
    if not obj:
        continue
    keys = list(obj.keys())
    if 'endpointId' in keys or 'location-context' in keys or 'paths' in keys or 'apiKey' in keys:
        print(f'--- island {i}: {json.dumps(obj, ensure_ascii=False)[:3000]}')
    if 'cam' in keys:
        print(f'--- island {i} cam: {json.dumps(obj["cam"], ensure_ascii=False)[:400]}')
    if 'cam-id' in keys:
        print(f'--- island {i} cam-id: {obj.get("cam-id")} url={obj.get("url")}')

# how many camId islands on this page?
ids = re.findall(r'camId&quot;:\[0,&quot;(\d+)&quot;\]', raw)
print('own-page slider camIds:', ids)
# JSON-LD places
for jm in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', raw, re.S):
    try:
        ld = json.loads(jm.group(1))
    except Exception:
        continue
    print('LD:', ld.get('@type'), json.dumps(ld, ensure_ascii=False)[:400])
# lat/lon raw in file?
print('has "latitude":', 'latitude' in raw, '| has "geo":', '"geo"' in raw)
