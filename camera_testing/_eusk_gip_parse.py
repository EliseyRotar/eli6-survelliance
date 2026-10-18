import re, glob, os, csv

ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
existing = {}
with open(ROOT + r'\controllable_Webcams.csv', newline='', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        u = ((r['live_stream_url'] or '') + ' ' + (r['url'] or '')).lower()
        if 'camaramar' in u or 'zumaia' in u or 'streamlock' in u:
            existing[(r['live_stream_url'] or '').lower()] = (r['csv_id'], r['type'], r['live_status'], (r['project_name'] or '')[:50])
print('existing streamlock/camaramar/zumaia rows:', len(existing))
for u, v in existing.items():
    if 'camaramar' in u or 'zumaia' in (v[3] or '').lower():
        print('  ', v, u[:100])
print()
pages = sorted(glob.glob(os.environ['TEMP'] + r'\gip_*.html')) + [os.environ['TEMP'] + r'\zumaia.html']
for p in pages:
    h = open(p, encoding='utf-8', errors='replace').read()
    urls = re.findall(r'https?://[^"\'\s<>\)]+\.m3u8', h)
    # titles near the video tag
    vids = re.findall(r'<video[^>]*>.*?</video>', h, re.S)
    print(os.path.basename(p), 'm3u8:', len(urls), 'video tags:', len(vids))
    for u in sorted(set(urls)):
        print('    ', u)
    # also look for plain img webcam shots
    for m in re.finditer(r'<source[^>]+src="([^"]+)"', h):
        print('    source:', m.group(1))
