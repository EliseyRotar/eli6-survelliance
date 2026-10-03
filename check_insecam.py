import json
p = r'C:\Users\eli6-admin\Documents\eli6-surveillance\insecam_fast_progress.json'
with open(p) as f:
    d = json.load(f)
# Show countries
for c in list(d.get('countries', {}).keys())[:10]:
    pg = d['countries'][c].get('_pages_done', 0)
    n_cams = len([k for k in d['countries'][c] if not k.startswith('_')])
    print(f'  {c}: {pg} pages, {n_cams} cams')
