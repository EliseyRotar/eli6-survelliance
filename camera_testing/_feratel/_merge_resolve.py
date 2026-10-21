import json, collections, sys, os

ROOT = os.path.dirname(os.path.abspath(__file__))
recs = [json.loads(l) for l in open(os.path.join(ROOT, 'cams2.jsonl'), encoding='utf-8')]
print(f'records: {len(recs)}')

main_exact = [r for r in recs if not r.get('main_from_slider')]
main_slider = [r for r in recs if r.get('main_from_slider')]
print(f'main object from own page: {len(main_exact)} | synthesized-from-slider/meta: {len(main_slider)}')
errs = collections.Counter(e for r in recs for e in r.get('errors', []))
print('errors:', dict(errs))

# cross-page registry of full cam objects
reg = {}
def register(c):
    cid = str(c.get('camId') or '')
    if not cid or not c.get('geo'):
        return
    cur = reg.get(cid)
    if cur is None:
        reg[cid] = c
    else:
        score = lambda x: sum(bool(x.get(k)) for k in ('contentUrl', 'mp4Url', 'poster', 'uploadDate', 'location', 'keywords'))
        if score(c) > score(cur):
            reg[cid] = c

for r in recs:
    if r.get('cam'):
        register(r['cam'])
    for c in r.get('related', []):
        register(c)
print(f'registry (with geo): {len(reg)}')

# resolve each page's true cam
resolved = []
no_geo = []
for r in recs:
    cid = str(r.get('url_camid'))
    own = r.get('cam') or {}
    own_is_own = str(own.get('camId')) == cid and own.get('geo')
    if own_is_own:
        cam, src = own, 'own-page'
    elif cid in reg:
        cam, src = reg[cid], 'cross-page'
    elif own.get('geo') and str(own.get('camId')) == cid:
        cam, src = own, 'own-page'
    else:
        # fall back: og_image poster id or camid_attr
        cam, src = None, 'unresolved'
        if str(r.get('camid_attr')) == cid and cid in reg:
            cam, src = reg[cid], 'cross-page'
    if cam is None:
        no_geo.append(r['page'])
        cam = {'camId': cid, 'name': own.get('name'), 'id': r.get('main_uuid')}
        src = 'no-geo'
    resolved.append({'page': r['page'], 'src': src, 'cam': cam,
                     'path': r.get('path'), 'related_ids': [str(c.get('camId')) for c in r.get('related', [])],
                     'video_object': r.get('video_object'), 'place': r.get('place'),
                     'og_image': r.get('og_image'), 'description': r.get('description'),
                     'og_title': r.get('og_title')})

srcs = collections.Counter(x['src'] for x in resolved)
print('resolution:', dict(srcs))
ids = set(str((x['cam'] or {}).get('camId')) for x in resolved)
print('distinct camIds:', len(ids))
with_geo = [x for x in resolved if (x['cam'].get('geo') or {}).get('latitude')]
print(f'with geo: {len(with_geo)}')
print('no-geo pages:', len(no_geo))
for p in no_geo[:15]:
    print('   ', p)

# geo source type: island vs jsonld place
place_only = 0
for x in with_geo:
    if x['src'] != 'own-page':
        place_only += 0
print('sample cross-page:', json.dumps(next((x for x in resolved if x['src'] == 'cross-page'), {}), ensure_ascii=False)[:700])

with open(os.path.join(ROOT, 'resolved.json'), 'w', encoding='utf-8') as f:
    json.dump(resolved, f, ensure_ascii=False)
print('wrote resolved.json')
