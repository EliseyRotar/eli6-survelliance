import csv
import json
import os
import subprocess
import tempfile

ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'


def probe(url, timeout=25):
    fd, tmp = tempfile.mkstemp(suffix='.bin')
    os.close(fd)
    try:
        p = subprocess.run(
            ['curl', '-sL', '-A', UA, '--max-time', str(timeout), '-o', tmp,
             '-w', '%{http_code}|%{content_type}|%{size_download}', url],
            capture_output=True, text=True, timeout=timeout + 10)
        meta = (p.stdout or '').strip().split('|')
        return (int(meta[0]) if meta and meta[0].isdigit() else 0,
                meta[1] if len(meta) > 1 else '',
                int(float(meta[2])) if len(meta) > 2 and meta[2] else 0)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


rows = list(csv.DictReader(open(ROOT + r'\controllable_Webcams.csv', newline='', encoding='utf-8')))
tv = [r for r in rows if 'crtvg.es' in ((r.get('live_stream_url') or '') + (r.get('url') or ''))]
print('crtvg rows in CSV:', len(tv))

cfg = json.load(open(os.environ['TEMP'] + r'\tiivii_cfg.json', encoding='utf-8'))
cfg_by_url = {c['url']: c for c in cfg['cameras']}

results = []
for r in sorted(tv, key=lambda x: x['csv_id']):
    u = r['live_stream_url'] or r['url']
    code, ctype, size = probe(u)
    in_cfg = u in cfg_by_url
    results.append({'csv_id': r['csv_id'], 'name': r['project_name'], 'url': u,
                    'in_cfg': in_cfg, 'code': code, 'ctype': ctype, 'size': size,
                    'live_status': r['live_status'], 'lat': r['lat'], 'lon': r['lon'],
                    'visibility': r['visibility'], 'type': r['type'],
                    'geo_source': r['geo_source'], 'notes': r['notes'][:60],
                    'poster_exists': os.path.exists(os.path.join(
                        ROOT, 'web_viewer', 'static', 'posters', r['idx'] + '.jpg'))})
    print('%s | %-46s | cfg=%-5s probe=%s %-24s %6sB | ls=%-4s vis=%-7s poster=%s | lat=%s lon=%s | %s' % (
        r['csv_id'], r['project_name'][:46], in_cfg, code, ctype[:24], size,
        repr(r['live_status']), repr(r['visibility']), results[-1]['poster_exists'],
        r['lat'] or '-', r['lon'] or '-', r['geo_source'] or '-'))

json.dump(results, open(os.environ['TEMP'] + r'\crtvg_inventory.json', 'w'),
          ensure_ascii=False, indent=1)
print('\nsummary: total=%d in_cfg=%d probe200=%d' % (
    len(results), sum(1 for x in results if x['in_cfg']),
    sum(1 for x in results if x['code'] == 200)))
