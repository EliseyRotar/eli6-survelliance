"""PSB (psb.li) ingest — all 14 broadcasts -> controllable_Webcams.csv.

Source: camera_testing/psb_dump.py output (psb_dump.json, full-detail dump).
At ingest time each broadcast is re-probed (streaming cfg -> master.m3u8 ->
thumb; the delivery backend is flappy), appended via csv_writer with
csv_id_prefix='psb', and the camera thumbnail is copied in as the poster.

Usage: python -X utf8 scripts/ingest/psb_ingest.py
"""
import csv
import json
import os
import sys
import time
import unicodedata
import urllib.request

sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')
import csv_writer  # noqa: E402

ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
DUMP_PATH = os.path.join(ROOT, 'camera_testing', 'psb_dump.json')
THUMB_DIR = os.path.join(ROOT, 'camera_testing', 'psb_thumbs')
POSTER_DIR = os.path.join(ROOT, 'web_viewer', 'static', 'posters')

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
HDR_KEYS = ('CamPos', 'CamTim', 'FrmRate', 'DataLen', 'AlmEvent', 'AutoFlip')

# Scene/geo enrichment from thumbnail montage analysis + on-page evidence.
ENRICH = {
    '4f01c8bdf26f': dict(
        name='Manhattan Skyline · New York, New York',
        subject='Midtown Manhattan skyline panorama at golden hour',
        category='city-skyline',
        country='United States', region='New York', city='New York',
        lat='40.7580', lon='-73.9855',
        precision='approximate_from_region', geo_src='psb:title+thumb'),
    '6629174af8cd': dict(
        name='Schermata multiview di una trasmissione televisiva in studio',
        subject='Italian TV studio multiview (RAI TGR Piemonte / Telecupole)',
        category='television',
        country='Italy', region='Piemonte', city='Turin',
        lat='45.0703', lon='7.6869',
        precision='approximate_from_region', geo_src='psb:tags(telecupole)+thumb'),
    'bac4bf7d560f': dict(
        name='Manpuku-ji Temple',
        subject='Japanese temple grounds, pagoda and stone lanterns',
        category='religious-site',
        country='Japan', geo_src='psb:title'),
    'f076a05cebbb': dict(
        name='PI6ZDM Amateur TV Repeater · Wormer, Netherlands',
        subject='Amateur radio ATV repeater multiview (PI6ZDM Wormer, BATC viewers)',
        category='television',
        country='Netherlands', region='Noord-Holland', city='Wormer',
        lat='52.5124', lon='4.8748',
        precision='approximate_from_region', geo_src='psb:thumb-overlay'),
    '277902943f73': dict(
        name='Residential entrance cam · Romania (Intrare)',
        subject='Night IR view of a residential driveway and gate, overlay Intrare',
        category='residential',
        country='Romania', geo_src='psb:thumb-overlay',
        scene='same_scene_broadcasts=277902943f73|5baa6155aaa6|769b0f59f519'),
    '5baa6155aaa6': dict(
        name='Residential entrance cam · Romania (Intrare)',
        subject='Night IR view of a residential driveway and gate, overlay Intrare',
        category='residential',
        country='Romania', geo_src='psb:thumb-overlay',
        scene='same_scene_broadcasts=277902943f73|5baa6155aaa6|769b0f59f519'),
    '769b0f59f519': dict(
        name='Residential entrance cam · Romania (Intrare)',
        subject='Night IR view of a residential driveway and gate, overlay Intrare',
        category='residential',
        country='Romania', geo_src='psb:thumb-overlay',
        scene='same_scene_broadcasts=277902943f73|5baa6155aaa6|769b0f59f519'),
    '3be2c56a50c1': dict(
        name='Blurry night cam · PSB 3be2c56',
        subject='Out-of-focus night scene with distant lights',
        category='', geo_src=''),
    '45a90e606a65': dict(
        name='Night outdoor cam · PSB 45a90e60',
        subject='Out-of-focus night scene, possible building structure',
        category='', geo_src=''),
    'bbde8fb2d630': dict(
        name='Night cam, dark frame · PSB bbde8fb2',
        subject='Near-black night frame with faint watermark',
        category='', geo_src=''),
    'bd92f7edfeab': dict(
        name='Night horizon lights cam · PSB bd92f7ed',
        subject='Night horizon with a chain of distant lights',
        category='', geo_src=''),
    'd6fdab854429': dict(
        name='AXIS P12-MkII cam, dark frame · PSB d6fdab85',
        subject='Dark frame, subject not visible (AXIS P12-MkII)',
        category='', brand='AXIS', model='P12-MkII', geo_src=''),
    '2ebcf3b72882': dict(
        name='PSB broadcast 2ebcf3b7 (placeholder)',
        subject='No image available (placeholder broadcast)',
        category='', geo_src=''),
    '8977da5458c4': dict(
        name='PSB broadcast 8977da54 (placeholder)',
        subject='No image available (placeholder broadcast)',
        category='', geo_src=''),
}


def ascii_s(s):
    return unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode('ascii')


def http_get(url, timeout=12):
    req = urllib.request.Request(url, headers=UA)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(262144)
            return r.status, dict(r.headers), body, round(time.time() - t0, 2)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), b'', round(time.time() - t0, 2)
    except Exception as e:
        return 0, {'error': type(e).__name__}, b'', round(time.time() - t0, 2)


def load_existing():
    urls, bcasts = set(), set()
    with open(csv_writer.CSV_PATH, encoding='utf-8', newline='') as f:
        for row in csv.DictReader(f):
            u = (row.get('url') or '').strip()
            if u:
                urls.add(u)
            notes = row.get('notes') or ''
            i = notes.find('broadcast_id=')
            if i >= 0:
                bcasts.add(notes[i + 13:i + 25])
    return urls, bcasts


def probe(rec):
    """Fresh probe: streaming cfg -> master m3u8 -> thumb (headers)."""
    bid = rec['id']
    st, hdrs, body, dt = http_get(f'https://www.psb.li/streaming/{bid}')
    main = ''
    if st == 200:
        try:
            cfg = json.loads(body.decode('utf-8', 'replace'))
            main = (cfg.get('playerConfig') or [{}])[0].get('mainStreamUrl', '') or ''
        except Exception:
            main = ''
    m3u8 = dict(status=0, ct='', server='')
    if main:
        s2, h2, b2, _ = http_get(main)
        if s2 != 200:
            time.sleep(1.5)
            s2, h2, b2, _ = http_get(main)
        m3u8 = dict(
            status=s2,
            ct=h2.get('Content-Type') or h2.get('content-type') or '',
            server=h2.get('Server') or h2.get('server') or '',
            is_m3u8=bool(b2 and (b2.lstrip()[:7] == b'#EXTM3U' or b'#EXTM3U' in b2[:2000])),
        )
    tst, thdr, tbody, _ = http_get(f'https://www.psb.li/thumb/{bid}')
    overlay = {k.lower(): thdr.get(k) for k in HDR_KEYS if thdr.get(k)}
    return dict(cfg=st, main=main, m3u8=m3u8, thumb=tst, thumb_body=tbody,
                thumb_ct=thdr.get('Content-Type', ''), overlay=overlay)


def build_entry(rec, probe_res, enrich):
    title = (rec.get('title') or '').strip()
    ld_name = (rec.get('ld_name') or '').strip()
    desc = (rec.get('description') or '').strip()
    ld_desc = (rec.get('ld_description') or '').strip()
    thumb = rec.get('thumb') or {}
    exif = {k: v for k, v in thumb.items() if k.startswith('exif_')}
    m3u8 = probe_res['m3u8']
    live = m3u8['status'] == 200 and m3u8.get('is_m3u8')

    notes = [
        'Family=psb', 'kind=hls', 'weight=40', 'source=psb',
        f'broadcast_id={rec["id"]}',
        f'streaming_status={probe_res["cfg"]}',
        f'm3u8_status={m3u8["status"]}',
        f'thumb={probe_res["thumb"]} {thumb.get("size") or ""}'.rstrip(),
    ]
    ov = probe_res['overlay']
    for k in ('campos', 'camtim', 'frmratio', 'almevent'):
        if ov.get(k):
            notes.append(f'{k}={ov[k]}')
    if exif:
        notes.append('exif=' + ' '.join(f'{k}:{v}' for k, v in sorted(exif.items())))
    if enrich.get('scene'):
        notes.append(enrich['scene'])

    return {
        'project_name': ascii_s(enrich.get('name') or title or ld_name or f'PSB broadcast {rec["id"]}'),
        'url': rec['watch_url'],
        'live_stream_url': probe_res['main'],
        'type': 'hls' if probe_res['main'] else '',
        'auth_required': '', 'auth_user': '', 'auth_pass': '',
        'enabled': 'True',
        'live_status': 'live' if live else 'unknown',
        'http_status': str(m3u8['status'] or probe_res['cfg']),
        'content_type': m3u8['ct'] or probe_res['thumb_ct'],
        'server_header': m3u8['server'],
        'page_title': ascii_s(title or ld_name or f'Broadcast {rec["id"]}'),
        'description': ascii_s(desc or ld_desc),
        'category': enrich.get('category', ''),
        'likely_subject': ascii_s(enrich.get('subject', '')),
        'brand': enrich.get('brand', ''),
        'model': enrich.get('model', ''),
        'country': enrich.get('country', ''),
        'region': enrich.get('region', ''),
        'city': enrich.get('city', ''),
        'zip': '', 'address': '', 'road': '',
        'location_precision': enrich.get('precision', ''),
        'lat': enrich.get('lat', ''),
        'lon': enrich.get('lon', ''),
        'geo_source': enrich.get('geo_src', ''),
        'isp': '', 'org': '', 'asn': '', 'reverse_dns': '',
        'host': 'www.psb.li',
        'confidence': 'high' if live else 'medium',
        'notes': ', '.join(notes),
        'csv_id_prefix': 'psb',
        'visibility': '',
    }


def main():
    with open(DUMP_PATH, encoding='utf-8') as f:
        dump = json.load(f)
    existing_urls, existing_bcasts = load_existing()
    print(f'[init] psb ingest: {len(dump)} dumped broadcasts, '
          f'{len(existing_urls)} existing csv rows')

    added, skipped, failed = [], [], []
    for bid in sorted(dump):
        rec = dump[bid]
        try:
            if bid in existing_bcasts or rec.get('watch_url') in existing_urls:
                skipped.append(bid)
                print(f'[skip] {bid} already ingested')
                continue
            pr = probe(rec)
            enrich = ENRICH.get(bid, {})
            entry = build_entry(rec, pr, enrich)
            blob = ' '.join(str(entry.get(k, '')) for k in
                            ('project_name', 'description', 'notes')).lower()
            if 'ip cam' in blob or 'insecam' in blob:
                print(f'[warn] {bid} text would trigger P7-ipcam-name, check name')
            idx = csv_writer.append_one(entry)
            if idx is None:
                failed.append(bid)
                print(f'[fail] {bid}: csv lock contention, no row written')
                continue
            poster = ''
            if pr['thumb'] == 200 and len(pr['thumb_body']) > 1000:
                dst = os.path.join(POSTER_DIR, f'{idx}.jpg')
                try:
                    with open(dst, 'wb') as f:
                        f.write(pr['thumb_body'])
                    poster = 'poster=ok'
                except Exception as e:
                    poster = f'poster=fail:{type(e).__name__}'
            elif os.path.isfile(os.path.join(THUMB_DIR, f'{bid}.jpg')):
                try:
                    with open(os.path.join(THUMB_DIR, f'{bid}.jpg'), 'rb') as f:
                        data = f.read()
                    with open(os.path.join(POSTER_DIR, f'{idx}.jpg'), 'wb') as f:
                        f.write(data)
                    poster = 'poster=local-fallback'
                except Exception as e:
                    poster = f'poster=fail:{type(e).__name__}'
            added.append(idx)
            print(f'[ok] {bid} -> idx={idx} cfg={pr["cfg"]} '
                  f'm3u8={pr["m3u8"]["status"]} thumb={pr["thumb"]} '
                  f'live={entry["live_status"]} {poster}')
            time.sleep(0.3)
        except Exception as e:
            failed.append(bid)
            print(f'[err] {bid}: {type(e).__name__}: {e}')

    print(f'[done] added={len(added)} skipped={len(skipped)} failed={len(failed)}')
    if added:
        print('idxs:', added)
    if failed:
        print('failed:', failed)
        sys.exit(1)


if __name__ == '__main__':
    main()
