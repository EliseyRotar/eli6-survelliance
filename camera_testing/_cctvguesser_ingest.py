# -*- coding: utf-8 -*-
"""Session 49: ingest CCTV Guesser cams (all 154, dedupe vs CSV).

Source: camera_testing/cctvguesser_raw.jsonl (154 records: HLS url,
exact lat/lng from the game's answer data, country/state/city).
Dedupe: normalized url (lower, scheme stripped, trailing slash) against
url + live_stream_url of every existing row, plus within-batch.
Liveness: GET each NEW m3u8 (#EXTM3U check) -> live_status/http_status.
Lock: os.open(CSV+'.lock', O_CREAT|O_EXCL) + tmp + os.replace.

State: camera_testing/cctvguesser_ingest.json
"""
import csv
import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
CSV = os.path.join(ROOT, 'controllable_Webcams.csv')
JSONL = os.path.join(ROOT, 'camera_testing', 'cctvguesser_raw.jsonl')
STATE = os.path.join(ROOT, 'camera_testing', 'cctvguesser_ingest.json')
DATE = date.today().isoformat()
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'

COUNTRY = {
    'us': 'United States', 'kr': 'South Korea', 'id': 'Indonesia',
    'th': 'Thailand', 'tr': 'Turkey', 'es': 'Spain', 'pl': 'Poland',
    'tt': 'Trinidad and Tobago', 'gb': 'United Kingdom', 'jp': 'Japan',
    'kg': 'Kyrgyzstan', 'mu': 'Mauritius', 'ro': 'Romania', 'ru': 'Russia',
    'sk': 'Slovakia',
}


def norm(u):
    u = (u or '').strip().lower()
    if u.startswith('https://'):
        u = u[8:]
    elif u.startswith('http://'):
        u = u[7:]
    return u.rstrip('/')


def probe(u, timeout=8):
    """GET m3u8 -> (http_code, ok_bool, content_type)."""
    try:
        req = urllib.request.Request(u, headers={
            'User-Agent': UA,
            'Accept': 'application/vnd.apple.mpegurl, */*',
        })
        with urllib.request.urlopen(req, timeout=timeout) as r:
            code = r.status
            ct = r.headers.get('Content-Type', '')
            body = r.read(4096)
        ok = code == 200 and (b'#EXTM3U' in body or 'mpegurl' in ct)
        return str(code), ok, (ct.split(';')[0] if ct else '')
    except urllib.error.HTTPError as e:
        return str(e.code), False, ''
    except Exception:
        return '', False, ''


def main():
    with open(JSONL, encoding='utf-8') as f:
        recs = [json.loads(l) for l in f if l.strip()]

    # existing normalized keys
    existing = set()
    max_idx = 0
    with open(CSV, encoding='utf-8-sig', errors='replace', newline='') as f:
        rd = csv.DictReader(f)
        hdr = rd.fieldnames
        for row in rd:
            try:
                max_idx = max(max_idx, int(row.get('idx') or 0))
            except ValueError:
                pass
            for k in ('url', 'live_stream_url'):
                n = norm(row.get(k))
                if n:
                    existing.add(n)

    # select new, dedupe within batch
    new, seen, skipped = [], set(), 0
    for rec in recs:
        n = norm(rec.get('url'))
        if not n or n in existing or n in seen:
            skipped += 1
            continue
        seen.add(n)
        new.append(rec)
    print('records=%d skip=%d new=%d max_idx=%d' % (len(recs), skipped, len(new), max_idx))

    # liveness probe for new
    codes = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(probe, r['url']): r for r in new}
        for fu in as_completed(futs):
            r = futs[fu]
            codes[r['id']] = fu.result()
    live_n = sum(1 for c in codes.values() if c[1])

    # build rows
    lock_path = CSV + '.lock'
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
    except FileExistsError:
        raise SystemExit('CSV lock held - aborting')

    try:
        rows_out = []
        idx = max_idx
        for rec in sorted(new, key=lambda x: (x.get('country_code') or '', x.get('name') or '')):
            idx += 1
            code, ok, ct = codes.get(rec['id'], ('', False, ''))
            host = urllib.parse.urlparse(rec['url']).hostname or ''
            cc = (rec.get('country_code') or '').lower()
            country = rec.get('country') or COUNTRY.get(cc, cc.upper())
            if not country.isascii():
                country = COUNTRY.get(cc, country)
            rows_out.append({
                'idx': str(idx),
                'project_name': '%s · CCTV Guesser · %s' % (country, rec.get('name') or rec['id'][:8]),
                'url': rec['url'],
                'live_stream_url': rec['url'],
                'type': 'hls',
                'auth_required': '', 'auth_user': '', 'auth_pass': '',
                'enabled': 'True',
                'live_status': 'live' if ok else '',
                'http_status': code,
                'content_type': ct or 'application/vnd.apple.mpegurl',
                'server_header': '',
                'page_title': '',
                'description': ('**traffic cam** public HLS stream; exact coords from '
                                'CCTV Guesser open-data game pool (%d OSD blackout region%s)'
                                % (len(rec.get('blackouts') or []),
                                   's' if len(rec.get('blackouts') or []) != 1 else '')),
                'category': 'traffic',
                'likely_subject': 'Road traffic',
                'brand': '', 'model': '',
                'country': country,
                'region': rec.get('state') or '',
                'city': rec.get('city') or '',
                'zip': '',
                'address': rec.get('display_name') or '',
                'road': '',
                'location_precision': 'precise',
                'lat': str(rec.get('lat', '')),
                'lon': str(rec.get('lng', '')),
                'geo_source': 'cctvguesser',
                'isp': '', 'org': '', 'asn': '', 'reverse_dns': '',
                'host': host,
                'confidence': 'high',
                'notes': ('cctvguesser_id=%s, source=cctvguesser, blackout_rects=%d, '
                          'ingested-%s' % (rec['id'], len(rec.get('blackouts') or []), DATE)),
                'csv_id': 'cg_' + rec['id'],
                'visibility': '',
            })

        # append with lock held, atomic replace
        tmp = CSV + '.tmp_ingest'
        with open(CSV, encoding='utf-8-sig', errors='replace', newline='') as f:
            existing_text = f.read()
        with open(tmp, 'w', encoding='utf-8-sig', newline='') as f:
            f.write(existing_text)
            if existing_text and not existing_text.endswith('\n'):
                f.write('\n')
            wr = csv.DictWriter(f, fieldnames=hdr, extrasaction='ignore')
            for r in rows_out:
                wr.writerow(r)
        os.replace(tmp, CSV)
    finally:
        try:
            os.remove(lock_path)
        except OSError:
            pass

    with open(STATE, 'w', encoding='utf-8') as f:
        json.dump({'date': DATE, 'records': len(recs), 'skipped': skipped,
                   'ingested': len(rows_out), 'idx_range': [max_idx + 1, idx],
                   'live': live_n, 'dead': len(rows_out) - live_n}, f, indent=1)
    print('INGESTED %d rows idx %d..%d live=%d' % (len(rows_out), max_idx + 1, idx, live_n))


if __name__ == '__main__':
    main()
