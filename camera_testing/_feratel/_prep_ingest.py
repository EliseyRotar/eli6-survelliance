import json, csv, collections, os, re

ROOT = os.path.dirname(os.path.abspath(__file__))
probes = [json.loads(l) for l in open(os.path.join(ROOT, 'live_probes.jsonl'), encoding='utf-8')]
none_cams = [p for p in probes if p.get('live_status') == 'none']
print('none cams:', len(none_cams))
print('og:image samples:')
for p in none_cams[:5]:
    print('  ', p['camid'], p.get('webtv_og_image'))

# location_precision / geo_source vocab
f = open(os.path.join(ROOT, '..', '..', 'controllable_Webcams.csv'), encoding='utf-8-sig', newline='')
rows = csv.DictReader(f)
lp = collections.Counter()
gs = collections.Counter()
tv = {}
for r in rows:
    lp[r['location_precision']] += 1
    gs[r['geo_source']] += 1
    m = re.search(r'media\.trafficvision\.live/feratel/(\d+)\.mp4', r['live_stream_url'] or '')
    if m:
        tv[m.group(1)] = r['idx']
print('location_precision:', lp.most_common(10))
print('geo_source:', gs.most_common(12))
print('trafficvision feratel ids:', len(tv))
json.dump(tv, open(os.path.join(ROOT, 'tv_feratel_map.json'), 'w'))

# overlap with our 1070
cams = json.load(open(os.path.join(ROOT, 'cams_final.json'), encoding='utf-8'))
our_ids = set(str(c['url_camid']) for c in cams)
ov = our_ids & set(tv)
print(f'overlap our camids with trafficvision rows: {len(ov)}')
# sample project_name styles for multi-source rows
