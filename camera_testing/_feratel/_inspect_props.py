import re, json, html, sys, glob

path = sys.argv[1] if len(sys.argv) > 1 else r'camera_testing\_feratel\cam1.html'
raw = open(path, encoding='utf-8', errors='replace').read()

# astro-island props are HTML-escaped JSON in the props attribute
props_list = re.findall(r'<astro-island[^>]*?props="([^"]+)"', raw)
print(f'islands found: {len(props_list)}')
for i, p in enumerate(props_list):
    try:
        obj = json.loads(html.unescape(p))
    except Exception as e:
        print(f'  island {i}: JSON fail {e}')
        continue
    keys = list(obj.keys())
    print(f'  island {i}: keys={keys}')
    # dig for cam-like dicts
    def walk(o, path=''):
        if isinstance(o, dict):
            if 'camId' in o or 'geo' in o or 'latitude' in o:
                print(f'    CAMLIKE at {path}: {json.dumps(o)[:800]}')
            for k, v in o.items():
                walk(v, f'{path}.{k}')
        elif isinstance(o, list):
            for j, v in enumerate(o[:5]):
                walk(v, f'{path}[{j}]')
    walk(obj)

# also search whole file for latitude context
for m in re.finditer(r'latitude', raw):
    s = max(0, m.start() - 200)
    print('LATCTX:', raw[s:m.start() + 300].replace('\n', ' ')[:500])
    break
else:
    print('no "latitude" in file')

for k in ('mp4Url', 'contentUrl', 'weather', 'kamerainformation', 'imageVersion'):
    hits = [m.start() for m in re.finditer(re.escape(k), raw)]
    if hits:
        s = max(0, hits[0] - 150)
        print(f'{k}: {len(hits)} hits, ctx: {raw[s:hits[0]+250]}')
    else:
        print(f'{k}: absent')
