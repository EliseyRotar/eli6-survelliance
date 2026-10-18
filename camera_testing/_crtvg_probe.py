import json
import os
import subprocess
import tempfile

cfg = json.load(open(os.environ['TEMP'] + r'\tiivii_cfg.json', encoding='utf-8'))
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


res = {'hls_ok': 0, 'hls_bad': [], 'thumb_ok': 0, 'thumb_bad': []}
for c in cfg['cameras']:
    u = c['url']
    code, ctype, size = probe(u)
    ok = code == 200 and 'mpegurl' in (ctype or '').lower()
    if ok:
        res['hls_ok'] += 1
    else:
        res['hls_bad'].append((c['name'], u, code, ctype, size))
    t = 'https://camarasweb.g24.gal' + c['thumbnail']
    tc, tct, ts = probe(t)
    tok = tc == 200 and ts > 3000
    if tok:
        res['thumb_ok'] += 1
    else:
        res['thumb_bad'].append((c['name'], t, tc, tct, ts))

# 4 static-only cams: try latest.png with static slug
for slug in ('catedral_nc', 'catedral_nl', 'ogrove', 'ortigueira'):
    t = 'https://camarasweb.g24.gal/assets/camarasweb.g24.gal/%s/latest.png' % slug
    tc, tct, ts = probe(t)
    print('static-only %-12s thumb: code=%s %s %sB' % (slug, tc, tct, ts))
    a = 'https://www.g24.gal/prog24/ARQUIVO/CAMARAS_WEB/%s.jpg' % slug
    ac, act_, asz = probe(a)
    print('static-only %-12s arquivo: code=%s %s %sB' % (slug, ac, act_, asz))

print('\nHLS ok: %d / %d' % (res['hls_ok'], len(cfg['cameras'])))
print('HLS bad:', res['hls_bad'])
print('thumb ok: %d / %d' % (res['thumb_ok'], len(cfg['cameras'])))
print('thumb bad:', res['thumb_bad'])
json.dump(res, open(os.environ['TEMP'] + r'\crtvg_probe.json', 'w'), indent=1)
