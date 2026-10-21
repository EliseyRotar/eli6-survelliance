import json, collections, os, statistics

ROOT = os.path.dirname(os.path.abspath(__file__))
probes = {json.loads(l)['camid']: json.loads(l) for l in open(os.path.join(ROOT, 'live_probes.jsonl'), encoding='utf-8')}
recs = json.load(open(os.path.join(ROOT, 'cams_final.json'), encoding='utf-8'))
print('probes:', len(probes))
st = collections.Counter(p.get('live_status') for p in probes.values())
print('status:', dict(st))
errs = collections.Counter((p.get('error') or '')[:30] for p in probes.values())
print('errors:', dict(errs))
ages = [p['frag_age_s'] for p in probes.values() if p.get('frag_age_s') is not None]
if ages:
    ages.sort()
    print(f'frag age: n={len(ages)} min={ages[0]} p50={ages[len(ages)//2]} p90={ages[int(len(ages)*.9)]} max={ages[-1]}')
live = [p for p in probes.values() if p.get('live_status') == 'live']
live_ages = sorted(p['frag_age_s'] for p in live if p.get('frag_age_s') is not None)
if live_ages:
    print(f'live-only age: min={live_ages[0]} p50={live_ages[len(live_ages)//2]} p90={live_ages[int(len(live_ages)*.9)]} max={live_ages[-1]}')
sizes = [p['frag_size'] for p in probes.values() if p.get('frag_size')]
print(f'frag sizes: n={len(sizes)} min={min(sizes)} max={max(sizes)} median={statistics.median(sizes)}')
# stale examples
for p in sorted((p for p in probes.values() if str(p.get('live_status','')).startswith('stale')), key=lambda x: -x.get('frag_age_s',0))[:8]:
    print('stale:', p['camid'], p.get('live_status'), p.get('frag_age_s'), 's')
# per-country live rate
byc = collections.defaultdict(lambda: [0,0])
for r in recs:
    c = (r.get('path') or {}).get('country')
    p = probes.get(str(r['url_camid'])) or {}
    byc[c][1] += 1
    if p.get('live_status') == 'live':
        byc[c][0] += 1
for c, (a, b) in sorted(byc.items(), key=lambda x: -x[1][1]):
    print(f'  {c}: {a}/{b} live')
# image-only cams: what do non-live cams give us? og image?
n_ogimg = sum(1 for p in probes.values() if p.get('webtv_og_image'))
print('webtv og:image present on non-live:', n_ogimg)
