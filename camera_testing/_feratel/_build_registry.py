import re, json, html, os, sys, collections

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

def deval(o):
    if isinstance(o, list):
        if len(o) == 2 and isinstance(o[0], int):
            if o[0] == 0:
                return deval(o[1])
            if o[0] == 1:
                return [deval(x) for x in o[1]]
        return [deval(x) for x in o]
    if isinstance(o, dict):
        return {k: deval(v) for k, v in o.items()}
    return o

def score(c):
    return sum(bool(c.get(k)) for k in ('contentUrl', 'mp4Url', 'poster', 'uploadDate',
                                         'location', 'keywords', 'slug', 'largeImageAvailable'))

reg = {}          # camId -> best object
def register(c):
    cid = str(c.get('camId') or '')
    if not cid:
        return
    cur = reg.get(cid)
    if cur is None or score(c) > score(cur):
        reg[cid] = c

# 1) cam pages
pages = [json.loads(l) for l in open(os.path.join(ROOT, 'cams2.jsonl'), encoding='utf-8')]
for r in pages:
    if r.get('cam'):
        register(r['cam'])
    for c in r.get('related', []):
        register(c)

# 2) region index pages
n_reg = 0
if os.path.exists(os.path.join(ROOT, 'region_cams.jsonl')):
    for l in open(os.path.join(ROOT, 'region_cams.jsonl'), encoding='utf-8'):
        o = json.loads(l)
        if 'cam' in o:
            register(o['cam'])
            n_reg += 1
print(f'region entries: {n_reg}')

# 3) homepage
home = os.path.join(ROOT, 'home_en.html')
if os.path.exists(home):
    raw = open(home, encoding='utf-8', errors='replace').read()
    for pm in re.finditer(r'<astro-island[^>]*?props="([^"]+)"', raw):
        try:
            obj = json.loads(html.unescape(pm.group(1)))
        except Exception:
            continue
        cam = obj.get('cam')
        if not cam:
            continue
        try:
            d = deval(cam)
        except Exception:
            continue
        if isinstance(d, dict) and d.get('camId') and (d.get('geo') or {}).get('latitude'):
            register(d)

print(f'registry total: {len(reg)}')
reg_geo = {k: v for k, v in reg.items() if (v.get('geo') or {}).get('latitude')}
print(f'registry with geo: {len(reg_geo)}')

# resolve pages
resolved = []
srcs = collections.Counter()
place_fallback = 0
for r in pages:
    cid = str(r.get('url_camid'))
    path = r.get('path') or {}
    cam = None
    geo_src = None
    if cid in reg_geo:
        own = r.get('cam') or {}
        if str(own.get('camId')) == cid and (own.get('geo') or {}).get('latitude'):
            cam, geo_src = own, 'astro-island-own'
        else:
            cam, geo_src = reg_geo[cid], 'astro-island-cross'
    else:
        # JSON-LD Place (location-level)
        place = r.get('place') or {}
        g = place.get('geo') or {}
        if g.get('latitude'):
            cam = {'camId': cid, 'name': place.get('name'),
                   'geo': {'latitude': g['latitude'], 'longitude': g.get('longitude')},
                   'id': r.get('main_uuid')}
            geo_src = 'jsonld-place'
            place_fallback += 1
        elif cid in reg:
            cam, geo_src = reg[cid], 'astro-island-nogeo'
    if cam is None:
        own = r.get('cam') or {}
        cam = {'camId': cid, 'name': own.get('name'), 'id': r.get('main_uuid')}
        geo_src = 'none'
    srcs[geo_src] += 1

    vo = r.get('video_object') or {}
    resolved.append({
        'page': r['page'],
        'url_camid': cid,
        'path': path,
        'name': cam.get('name') or (r.get('og_title') or '').replace('Webcams in ', ''),
        'location': cam.get('location'),
        'keywords': cam.get('keywords') or [],
        'cam_uuid': cam.get('id') or r.get('main_uuid'),
        'lat': (cam.get('geo') or {}).get('latitude'),
        'lon': (cam.get('geo') or {}).get('longitude'),
        'geo_source': geo_src,
        'contentUrl': cam.get('contentUrl'),
        'mp4Url': cam.get('mp4Url') or (vo.get('contentUrl')),
        'poster': cam.get('poster') or r.get('og_image'),
        'uploadDate': cam.get('uploadDate') or vo.get('uploadDate'),
        'description': vo.get('description') or r.get('description'),
        'embedUrl': vo.get('embedUrl'),
        'thumbnailUrl': vo.get('thumbnailUrl'),
        'largeImageAvailable': cam.get('largeImageAvailable'),
        'place_name': (r.get('place') or {}).get('name'),
    })

print('geo sources:', dict(srcs))
with_geo = [x for x in resolved if x['lat'] is not None]
print(f'resolved with geo: {len(with_geo)}/{len(resolved)}')
missing = [x for x in resolved if x['lat'] is None]
print(f'still missing geo: {len(missing)}')
for x in missing[:20]:
    print('   ', x['page'])

outp = os.path.join(ROOT, 'cams_final.json')
json.dump(resolved, open(outp, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print('wrote cams_final.json', len(resolved))
