import csv, json, os, re, sys, ssl, socket, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(ROOT, '..', '..'))
CSV = os.path.join(REPO, 'controllable_Webcams.csv')
LOCK = CSV + '.lock'
sys.path.insert(0, ROOT)
from _ingest import resolve_host, ripe, rdns, http_probe

cams2 = {}
for l in open(os.path.join(ROOT, 'cams2.jsonl'), encoding='utf-8'):
    o = json.loads(l)
    cams2[str(o.get('url_camid'))] = o.get('og_title') or ''
probes = {json.loads(l)['camid']: json.loads(l)
          for l in open(os.path.join(ROOT, 'live_probes.jsonl'), encoding='utf-8')}

fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
try:
    rows = list(csv.DictReader(open(CSV, encoding='utf-8-sig', newline='')))
    header = list(rows[0].keys())

    # patch ft rows
    stale_hosts = set()
    for r in rows:
        cid_r = r['csv_id']
        if not cid_r.startswith('ft_'):
            continue
        cid = cid_r[3:]
        ls = r['live_status']
        if ls == 'stale-10m':
            r['live_status'] = 'stale'
        elif ls == 'none':
            r['live_status'] = 'still_image'
        if not r['page_title']:
            r['page_title'] = cams2.get(cid) or f"Webcams in {r['project_name'].split(' · feratel · ', 1)[-1]} - Livecams in HD"
        # stale rows were mis-written as image: restore video fields
        if ls == 'stale-10m':
            p = probes.get(cid, {})
            r['type'] = 'video'
            r['live_stream_url'] = p.get('live_url') or ''
            r['http_status'] = str(p.get('http_status') or '')
            r['content_type'] = 'video/mp4'
            r['server_header'] = 'Apache'
            parts = [x.strip() for x in r['notes'].split(',') if x.strip()]
            parts = [x for x in parts if not x.startswith('still_image')]
            parts = [x for x in parts if not x.startswith('frag_') and x != 'rotating_fragment (webtv t=1 og:video, re-poll for new frag)']
            head = parts[0] if parts else f'feratel camid={cid}'
            rest = [x for x in parts[1:] if not x.startswith('webtv=') and not x.startswith('latest_mp4=') and not x.startswith('ipcamlive') and not x.startswith('ingested')]
            keep = [x for x in parts if x.startswith(('webtv=', 'latest_mp4=', 'ipcamlive', 'place_geo='))]
            new = [head, f'frag_age={p.get("frag_age_s")}s', f'frag_size={p.get("frag_size")}',
                   'rotating_fragment (webtv t=1 og:video, re-poll for new frag)'] + keep
            ing = [x for x in parts if x.startswith('ingested')]
            new += ing
            r['notes'] = ', '.join(new)
            host = urllib.parse.urlsplit(r['live_stream_url']).hostname or ''
            r['host'] = host
            stale_hosts.add(host)
        elif ls == 'none':
            # keep image fields, ensure note marker
            if 'still_image' not in r['notes']:
                r['notes'] = r['notes'].replace('feratel', 'feratel still_image', 1)

    # whois for stale hosts (likely distinct sts IPs already covered, but check)
    ips = {}
    for h in stale_hosts:
        ips[h] = resolve_host(h)
    uniq = sorted({ip for ip in ips.values() if ip})
    meta = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(ripe, ip): ip for ip in uniq}
        for f in futs:
            try:
                meta[futs[f]] = f.result()
            except Exception:
                meta[futs[f]] = ('', '', '')
    rdnsm = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(rdns, ip): ip for ip in uniq}
        for f in futs:
            try:
                rdnsm[futs[f]] = f.result()
            except Exception:
                rdnsm[futs[f]] = ''
    for r in rows:
        if not r['csv_id'].startswith('ft_') or r['live_status'] != 'stale':
            continue
        host = urllib.parse.urlsplit(r['live_stream_url']).hostname or ''
        ip = ips.get(host)
        if ip:
            r['isp'], r['org'], r['asn'] = meta.get(ip, ('', '', ''))
            r['reverse_dns'] = rdnsm.get(ip, '')

    tmp = CSV + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, CSV)
    print(f'patched. rows={len(rows)}')
finally:
    os.close(fd)
    if os.path.exists(LOCK):
        os.remove(LOCK)

# verify
rows = list(csv.DictReader(open(CSV, encoding='utf-8-sig', newline='')))
ft = [r for r in rows if r['csv_id'].startswith('ft_')]
import collections
print('ft:', len(ft), collections.Counter(r['live_status'] for r in ft))
print('type:', collections.Counter(r['type'] for r in ft))
print('missing live_url on video rows:', sum(1 for r in ft if r['type'] == 'video' and not r['live_stream_url']))
print('missing page_title:', sum(1 for r in ft if not r['page_title']))
print('stale sample:', next(r['live_stream_url'] for r in ft if r['live_status'] == 'stale'))
