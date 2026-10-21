import json, collections, sys

path = sys.argv[1] if len(sys.argv) > 1 else 'camera_testing\\_feratel\\cams.jsonl'
recs = [json.loads(l) for l in open(path, encoding='utf-8')]
print(f'records: {len(recs)}')
has_cam = [r for r in recs if r.get('cam')]
has_geo = [r for r in has_cam if (r['cam'].get('geo') or {}).get('latitude')]
has_main_id = [r for r in has_cam if str(r['cam'].get('camId')) == str(r.get('url_camid'))]
errs = collections.Counter(e.split(':')[0] for r in recs for e in r.get('errors', []))
print(f'has cam object: {has_cam} | with geo: {len(has_geo)} | main==url id: {len(has_main_id)}')
print(f'errors: {dict(errs)}')
missing_geo = [r for r in has_cam if not (r['cam'].get('geo') or {}).get('latitude')]
print(f'missing geo: {len(missing_geo)}')
for r in missing_geo[:8]:
    print('  no-geo:', r['page'])
no_cam = [r for r in recs if not r.get('cam')]
for r in no_cam[:8]:
    print('  no-cam:', r['page'], r.get('errors'))
mism = [r for r in has_cam if str(r['cam'].get('camId')) != str(r.get('url_camid'))]
for r in mism[:8]:
    print(f"  mismatch: {r['page']} url={r.get('url_camid')} cam={r['cam'].get('camId')}")

# distinct camIds + countries
ids = set(str(r['cam']['camId']) for r in has_cam)
print(f'distinct camIds: {len(ids)}')
ctry = collections.Counter(r.get('path', {}).get('country') for r in recs)
print('countries:', dict(ctry))
# sample record
print('SAMPLE:', json.dumps(has_geo[0], ensure_ascii=False)[:1200])
