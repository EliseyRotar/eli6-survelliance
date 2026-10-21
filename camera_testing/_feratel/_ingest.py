import csv, json, os, re, sys, time, ssl, socket, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(ROOT, '..', '..'))
CSV = os.path.join(REPO, 'controllable_Webcams.csv')
LOCK = CSV + '.lock'
TODAY = date.today().isoformat()
CTX = ssl.create_default_context()
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0'}
FIELDNAMES = ['idx', 'project_name', 'url', 'live_stream_url', 'type', 'auth_required', 'auth_user',
              'auth_pass', 'enabled', 'live_status', 'http_status', 'content_type', 'server_header',
              'page_title', 'description', 'category', 'likely_subject', 'brand', 'model', 'country',
              'region', 'city', 'zip', 'address', 'road', 'location_precision', 'lat', 'lon',
              'geo_source', 'isp', 'org', 'asn', 'reverse_dns', 'host', 'confidence', 'notes',
              'csv_id', 'visibility']

COUNTRY = {'andorra': 'Andorra', 'austria': 'Austria', 'belgium': 'Belgium',
           'czech-republic': 'Czech Republic', 'germany': 'Germany', 'greenland': 'Greenland',
           'italy': 'Italy', 'republic-of-san-marino': 'San Marino', 'slovakia': 'Slovakia',
           'spain': 'Spain', 'switzerland': 'Switzerland'}

MOUNTAIN = re.compile(r'bergstation|talstation|gletscher|ski|lift|seilbahn|bahn\b|alm\b|kogel|horn\b|joch\b|'
                      r'sattel|wand\b|flyingcam|gipfel|hoch\b|pass\b|h[uü]tte|peak|glacier|summit|ridge|'
                      r'snow|schnee|rodel|piste|folge|kov|\balm-|wander|alp\b|tal\b|flying|panorama|'
                      r'mountain', re.I)
COAST = re.compile(r'strand|playa|cala\b|beach|bucht|laguna|costa|hafen|harbour|harbor|kueste|küste|'
                   r'meer\b|ocean|insel|island|dike|deich|bay\b|marina|porto|golfo|phare|lighthouse|'
                   r'nerang|norddeich|seeblick|sunset', re.I)
WATER = re.compile(r'\bsee\b|see-|lake|fluss|river|wasserfall|fall\b|talsperre|reservoir|dam\b|brücke|'
                   r'bridge|kanal|canal|gulf\b|wasser|water|weiher|moor', re.I)
CITY = re.compile(r'stadt\b|rathaus|platz\b|markt\b|city\b|downtown|hochhaus|zentrum|studio|\borf\b|'
                  r'\bsrf\b|\brts\b|kirche|church|brücke|strasse|straße|straße\b|urban|station\b|'
                  r'hotel\b|bahnhof|parkplatz|parking|città|citta|palazzo|view of|skyline|dorf\b|'
                  r'village|city of', re.I)
TRAFFIC = re.compile(r'autobahn|highway|kreisel|roundabout|verkehr|traffic|intersection|road\b|'
                     r'kreuzung|straße|strasse', re.I)


def absu(u):
    if not u:
        return ''
    if u.startswith('//'):
        return 'https:' + u
    return u


def derive(text):
    t = text or ''
    if TRAFFIC.search(t):
        return 'traffic', 'Road traffic'
    if MOUNTAIN.search(t):
        return 'mountain', 'Mountain / ski area'
    if COAST.search(t):
        return 'coast', 'Coast / seaside'
    if WATER.search(t):
        return 'water', 'Lake / river'
    if CITY.search(t):
        return 'city', 'Urban view'
    return 'scenic', 'Scenic view'


def http_probe(url, want_range=False, timeout=20):
    out = {}
    try:
        hdrs = dict(UA)
        if want_range:
            hdrs['Range'] = 'bytes=0-0'
        req = urllib.request.Request(url, headers=hdrs)
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            out['status'] = r.status
            out['content_type'] = r.headers.get('Content-Type', '')
            out['server'] = r.headers.get('Server', '')
            if want_range:
                cr = r.headers.get('Content-Range', '')
                out['size'] = int(cr.rsplit('/', 1)[1]) if '/' in cr else None
                out['etag'] = r.headers.get('ETag', '')
            r.read(4096)
    except urllib.error.HTTPError as e:
        out['status'] = e.code
        out['error'] = f'HTTP {e.code}'
    except Exception as e:
        out['error'] = repr(e)[:100]
    return out


def resolve_host(host):
    try:
        return socket.gethostbyname(host)
    except Exception:
        return None


def ripe(ip):
    try:
        u = 'https://rest.db.ripe.net/search.json?query-string=' + ip + '&flags=no-personal'
        req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
        d = json.load(urllib.request.urlopen(req, timeout=15, context=CTX))
        isp = org = asn = ''
        for o in d.get('objects', {}).get('object', []):
            attrs = {a['name']: a['value'] for a in o.get('attributes', {}).get('attribute', [])}
            if o.get('type') == 'route' and not asn:
                asn = attrs.get('origin', '')
            if o.get('type') == 'organisation' and not org:
                org = attrs.get('org-name', '')
            if o.get('type') == 'inetnum' and not isp:
                isp = attrs.get('netname', '')
        return isp, org, asn
    except Exception:
        return '', '', ''


def rdns(ip):
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return ''


def main():
    # reuse image probes if previously made
    cams = json.load(open(os.path.join(ROOT, 'cams_final.json'), encoding='utf-8'))
    probes = {json.loads(l)['camid']: json.loads(l)
              for l in open(os.path.join(ROOT, 'live_probes.jsonl'), encoding='utf-8')}
    tv = json.load(open(os.path.join(ROOT, 'tv_feratel_map.json'), encoding='utf-8'))

    lock_fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        with open(CSV, encoding='utf-8-sig', newline='') as f:
            rows = list(csv.DictReader(f))
            header = list(rows[0].keys())
        existing_ids = set()
        max_idx = -1
        for r in rows:
            if r['csv_id'].startswith('ft_'):
                existing_ids.add(r['csv_id'][3:])
            if r['idx'].isdigit():
                max_idx = max(max_idx, int(r['idx']))
        next_idx = max_idx + 1
        print(f'csv rows={len(rows)} next_idx={next_idx} existing ft_={len(existing_ids)}')

        # probe image cams (193)
        img_urls = {}
        for c in cams:
            cid = str(c['url_camid'])
            p = probes.get(cid, {})
            if p.get('live_status') == 'none' and p.get('webtv_og_image'):
                img_urls[cid] = absu(p['webtv_og_image'])
        print(f'probing {len(img_urls)} image urls...')
        img_res = {}
        with ThreadPoolExecutor(max_workers=10) as ex:
            futs = {ex.submit(http_probe, u): cid for cid, u in img_urls.items()}
            for fut in as_completed(futs):
                cid = futs[fut]
                img_res[cid] = fut.result()
        ok_img = sum(1 for v in img_res.values() if v.get('status') == 200)
        print(f'image probes ok={ok_img}/{len(img_res)}')

        # resolve + whois unique hosts
        hosts = set()
        for c in cams:
            cid = str(c['url_camid'])
            p = probes.get(cid, {})
            if p.get('live_url'):
                hosts.add(urllib.parse.urlsplit(p['live_url']).hostname or '')
            elif cid in img_urls:
                hosts.add(urllib.parse.urlsplit(img_urls[cid]).hostname or '')
        hosts.discard('')
        print(f'unique hosts: {len(hosts)}')
        ip_of = {}
        with ThreadPoolExecutor(max_workers=10) as ex:
            futs = {ex.submit(resolve_host, h): h for h in hosts}
            for fut in as_completed(futs):
                h = futs[fut]
                try:
                    ip_of[h] = fut.result()
                except Exception:
                    ip_of[h] = None
        uniq_ips = sorted({ip for ip in ip_of.values() if ip})
        print(f'unique ips: {len(uniq_ips)} -> whois...')
        meta = {}
        with ThreadPoolExecutor(max_workers=6) as ex:
            futs = {ex.submit(ripe, ip): ip for ip in uniq_ips}
            for fut in as_completed(futs):
                ip = futs[fut]
                try:
                    meta[ip] = fut.result()
                except Exception:
                    meta[ip] = ('', '', '')
        rdnsm = {}
        with ThreadPoolExecutor(max_workers=8) as ex:
            futs = {ex.submit(rdns, ip): ip for ip in uniq_ips}
            for fut in as_completed(futs):
                ip = futs[fut]
                try:
                    rdnsm[ip] = fut.result()
                except Exception:
                    rdnsm[ip] = ''

        new_rows = []
        n_dup = 0
        for c in cams:
            cid = str(c['url_camid'])
            if cid in existing_ids:
                n_dup += 1
                continue
            p = probes.get(cid, {})
            status = p.get('live_status') or 'unknown'
            path = c.get('path') or {}
            country_en = COUNTRY.get(path.get('country'), (path.get('country') or '').title())
            region = (path.get('region') or '').replace('-', ' ').title() if path.get('region') else ''
            name = (c.get('name') or '').strip() or (c.get('og_title') or '').replace('Webcams in ', '')
            location = c.get('location') or ''
            city = re.sub(r'\s*\([^)]*\)', '', location).strip()
            kw = c.get('keywords') or []
            text = ' '.join([name, location, ' '.join(kw), c.get('page') or ''])
            cat, subject = derive(text)

            notes = [f'feratel camid={cid}']
            if status in ('live', 'stale'):
                live_url = p.get('live_url')
                notes.append(f'frag_age={p.get("frag_age_s")}s')
                notes.append(f'frag_size={p.get("frag_size")}')
                notes.append('rotating_fragment (webtv t=1 og:video, re-poll for new frag)')
                http_status = str(p.get('http_status') or '')
                ctype = 'video/mp4'
                server = 'Apache'
            else:
                live_url = img_urls.get(cid, '')
                http_status = str((img_res.get(cid) or {}).get('status') or '')
                ctype = (img_res.get(cid) or {}).get('content_type', '') or 'image/jpeg'
                server = (img_res.get(cid) or {}).get('server', '')
                notes.append('still_image (webtv t=1 has no og:video)')

            cu = absu(c.get('contentUrl'))
            if cu:
                notes.append(f'webtv={cu}')
            if c.get('mp4Url'):
                notes.append(f'latest_mp4={c["mp4Url"]}')
            if c.get('geo_source') == 'jsonld-place':
                notes.append(f'place_geo={c.get("place_name")}')
            if cid in tv:
                notes.append(f'ipcamlive_mirror_idx={tv[cid]}')
            notes.append(f'ingested-{TODAY}')

            host = urllib.parse.urlsplit(live_url).hostname if live_url else ''
            ip = ip_of.get(host)
            isp, org, asn = meta.get(ip, ('', '', ''))

            row = {
                'idx': str(next_idx),
                'project_name': f'{country_en} · feratel · {name}',
                'url': c['page'],
                'live_stream_url': live_url or '',
                'type': 'video' if status in ('live', 'stale') else 'image',
                'auth_required': '', 'auth_user': '', 'auth_pass': '',
                'enabled': 'True',
                'live_status': status,
                'http_status': http_status,
                'content_type': ctype,
                'server_header': server,
                'page_title': c.get('og_title') or '',
                'description': (c.get('description') or '')[:490],
                'category': cat,
                'likely_subject': subject,
                'brand': '', 'model': '',
                'country': country_en,
                'region': region,
                'city': city,
                'zip': '', 'address': '', 'road': '',
                'location_precision': 'precise' if c.get('geo_source') == 'astro-island-cross' or c.get('geo_source') == 'astro-island-own' else 'approximate_from_region',
                'lat': f"{c['lat']:.6f}" if c.get('lat') is not None else '',
                'lon': f"{c['lon']:.6f}" if c.get('lon') is not None else '',
                'geo_source': 'feratel.com' if c.get('geo_source', '').startswith('astro') else 'feratel.com#jsonld-place',
                'isp': isp, 'org': org, 'asn': asn,
                'reverse_dns': rdnsm.get(ip, '') if ip else '',
                'host': host or 'www.feratel.com',
                'confidence': 'high' if c.get('geo_source', '').startswith('astro') else 'medium',
                'notes': ', '.join(notes),
                'csv_id': f'ft_{cid}',
                'visibility': 'public',
            }
            new_rows.append(row)
            next_idx += 1

        print(f'new rows={len(new_rows)} dups_skipped={n_dup}')
        if not new_rows:
            print('nothing to add')
            return

        tmp = CSV + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=header)
            w.writeheader()
            w.writerows(rows)
            for r in new_rows:
                w.writerow({k: r.get(k, '') for k in header})
        os.replace(tmp, CSV)
        print(f'CSV now {len(rows) + len(new_rows)} rows, wrote idx {new_rows[0]["idx"]}..{new_rows[-1]["idx"]}')
    finally:
        os.close(lock_fd)
        if os.path.exists(LOCK):
            os.remove(LOCK)


if __name__ == '__main__':
    main()
