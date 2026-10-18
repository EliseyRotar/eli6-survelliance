import re, json, html, csv, collections

raw = open(r'C:\Users\ELI6-A~1\AppData\Local\Temp\cic_listado.html', encoding='iso-8859-1').read()
entries = []
tokens = re.finditer(
    r'<h4>(.*?)</h4>|camaras_def/cam_web_(\d+)_(\d+)_def\.html"[^>]*>(.*?)</a>',
    raw, re.S)
group = None
for m in tokens:
    if m.group(1):
        group = html.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip()
    else:
        name = html.unescape(re.sub(r'<[^>]+>', '', m.group(4))).strip()
        entries.append({'A': m.group(2), 'B': m.group(3), 'name': name, 'group': group})
print('list entries:', len(entries))
gcount = collections.Counter(e['group'] for e in entries)
for k, v in gcount.items():
    print(f'  {v:3} {k}')

by_key = {}
for e in entries:
    by_key[f"{e['A']}-{e['B']}"] = e

root = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
csv_rows = []
with open(root + r'\controllable_Webcams.csv', newline='', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        blob = (r['url'] or '') + ' ' + (r['live_stream_url'] or '')
        if 'cic.tenerife' in blob:
            m = re.search(r'camara-(\d+)-(\d+)\.jpg', blob)
            csv_rows.append({'csv_id': r['csv_id'], 'key': (f"{m.group(1)}-{m.group(2)}" if m else None),
                             'name': r['project_name'], 'lat': r['lat'], 'lon': r['lon']})
print('csv cic rows:', len(csv_rows), '| matched in list:', sum(1 for c in csv_rows if c['key'] in by_key))
unmatched_csv = [c for c in csv_rows if c['key'] not in by_key]
unmatched_list = [e for e in entries if f"{e['A']}-{e['B']}" not in {c['key'] for c in csv_rows}]
print('csv-not-in-list:', len(unmatched_csv), [c['key'] for c in unmatched_csv[:10]])
print('list-not-in-csv:', len(unmatched_list), [(e['A'], e['B']) for e in unmatched_list[:10]])
for c in csv_rows[:5]:
    e = by_key.get(c['key'])
    print('  ', c['key'], '->', (e['name'] + ' | ' + e['group']) if e else 'NO MATCH', '| was:', c['name'][:35])
json.dump(entries, open(root + r'\camera_testing\_es_tenerife_list.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('saved _es_tenerife_list.json')
