import csv
import collections

ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
keys = ('meteogalicia', 'gijon', 'gijón', 'torrevieja', 'campoamor', 'webcamurcia',
        'sierra nevada', 'ibiza', 'reus', 'girona', 'gerona', 'vigo', 'muxia',
        'huelva', 'cadiz', 'c\u00e1diz', 'lanzarote', 'gomera', 'las palmas',
        'ubiña', 'salinas', 'cuenca', 'toledo', 'valladolid', 'navarra',
        'extremadura', 'rioja', 'aemet', 'junta de andaluc')
hits = collections.Counter()
samples = collections.defaultdict(list)
with open(ROOT + r'\controllable_Webcams.csv', newline='', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        if not (r['country'] or '').startswith('Spain'):
            continue
        blob = ((r['project_name'] or '') + ' ' + (r['url'] or '') + ' ' +
                (r['live_stream_url'] or '') + ' ' + (r['city'] or '') + ' ' +
                (r['org'] or '') + ' ' + (r['notes'] or '')).lower()
        for k in keys:
            if k in blob:
                hits[k] += 1
                if len(samples[k]) < 2:
                    samples[k].append((r['csv_id'], (r['project_name'] or '')[:50]))
for k in keys:
    print('%5d  %-18s %s' % (hits[k], k, samples[k]))
