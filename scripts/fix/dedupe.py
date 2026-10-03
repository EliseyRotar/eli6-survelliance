import json
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\africam_new_35.json') as f:
    data = json.load(f)
clean = []
for r in data:
    primary = r.get('yt_id')
    secs = []
    seen = {primary}
    for s in r.get('secondary_cams', []):
        if s['yt_id'] not in seen:
            secs.append(s)
            seen.add(s['yt_id'])
    r['secondary_cams'] = secs
    clean.append(r)
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\africam_new_35.json', 'w') as f:
    json.dump(clean, f, indent=2, ensure_ascii=False)
print(f'Cleaned. {len(clean)} entries.')
for r in clean:
    n = len(r.get('secondary_cams', []))
    if n > 0:
        ids = [s['yt_id'] for s in r['secondary_cams']]
        print(f"{r['lodge']}: primary={r['yt_id']}, +{n} cams: {ids}")
