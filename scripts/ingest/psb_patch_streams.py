"""Patch the 14 psb rows with stream config + fresh liveness.

The initial psb_ingest.py pass ran while www.psb.li/streaming/ was
hanging, so live_stream_url/type landed empty. This pass:
  1. re-probes /streaming/<id> (40s) and delivery1 master.m3u8 (10s)
  2. falls back to the mainStreamUrl observed in psb_dump.json
  3. rewrites the psb rows in place under the csv_writer lock.

Usage: python -X utf8 scripts/ingest/psb_patch_streams.py
"""
import csv
import json
import os
import sys
import time
import urllib.request

ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
CSV_PATH = os.path.join(ROOT, 'controllable_Webcams.csv')
DUMP_PATH = os.path.join(ROOT, 'camera_testing', 'psb_dump.json')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}


def http_get(url, timeout=10):
    req = urllib.request.Request(url, headers=UA)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(65536)
            return r.status, dict(r.headers), body, round(time.time() - t0, 1)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), b'', round(time.time() - t0, 1)
    except Exception as e:
        return 0, {'error': type(e).__name__}, b'', round(time.time() - t0, 1)


def probe(bid, cfg_main):
    st, hdrs, body, dt = http_get(f'https://www.psb.li/streaming/{bid}', timeout=40)
    main = ''
    if st == 200:
        try:
            main = (json.loads(body.decode('utf-8', 'replace'))
                    .get('playerConfig') or [{}])[0].get('mainStreamUrl', '') or ''
        except Exception:
            main = ''
    if not main:
        main = cfg_main or ''
    m = dict(status=0, ct='', server='', ok=False)
    if main:
        s2, h2, b2, _ = http_get(main, timeout=10)
        if s2 != 200:
            time.sleep(1.0)
            s2, h2, b2, _ = http_get(main, timeout=10)
        m = dict(
            status=s2,
            ct=h2.get('Content-Type') or h2.get('content-type') or '',
            server=h2.get('Server') or h2.get('server') or '',
            ok=bool(b2 and b2.lstrip()[:7] == b'#EXTM3U'),
        )
    return dict(cfg=st, main=main, m3u8=m, cfg_dt=dt)


def set_note(notes, key, val):
    import re
    out = re.sub(rf'\b{key}=[^,]*', f'{key}={val}', notes)
    if out == notes and f'{key}=' not in notes:
        out = (notes + ', ' if notes else '') + f'{key}={val}'
    return out


def main():
    with open(DUMP_PATH, encoding='utf-8') as f:
        dump = json.load(f)
    watch_urls = {r['watch_url']: bid for bid, r in dump.items()}

    # lock + read (same protocol as csv_writer.append_one)
    lock_fd = None
    for attempt in range(80):
        try:
            lock_fd = os.open(CSV_PATH + '.lock', os.O_CREAT | os.O_EXCL | os.O_RDWR)
            break
        except FileExistsError:
            time.sleep(0.05 + 0.03 * (attempt % 10))
    if lock_fd is None:
        print('[fatal] could not take csv lock')
        sys.exit(1)

    try:
        with open(CSV_PATH, encoding='utf-8', newline='') as f:
            rows = list(csv.reader(f))
        header = rows[0]
        H = {name: i for i, name in enumerate(header)}

        patched = 0
        for row in rows[1:]:
            if len(row) < len(header):
                continue
            bid = watch_urls.get(row[H['url']])
            if not bid:
                continue
            rec = dump[bid]
            cfg_main = (rec.get('streaming') or {}).get('main') or ''
            pr = probe(bid, cfg_main)
            # delivery1 is elastic: master.m3u8 404s while a stream is idle
            # (observed flapping 200->404->200 within minutes), so an observed
            # mainStreamUrl (fresh or from dump) means the broadcast is live;
            # m3u8 404 alone is not evidence of removal (removal = cfg 404).
            live = bool(pr['main'])

            if pr['main']:
                row[H['live_stream_url']] = pr['main']
                row[H['type']] = 'hls'
                row[H['content_type']] = pr['m3u8']['ct'] or 'application/vnd.apple.mpegurl'
                row[H['server_header']] = pr['m3u8']['server'] or row[H['server_header']]
            row[H['live_status']] = 'live' if live else 'unknown'
            if pr['m3u8']['status']:
                row[H['http_status']] = str(pr['m3u8']['status'])
            elif pr['cfg']:
                row[H['http_status']] = str(pr['cfg'])
            row[H['confidence']] = 'high' if live else 'medium'
            n = row[H['notes']]
            n = set_note(n, 'streaming_status', str(pr['cfg']))
            n = set_note(n, 'm3u8_status', str(pr['m3u8']['status']))
            if live:
                n = set_note(n, 'probed_live', time.strftime('%Y-%m-%dT%H:%M'))
            row[H['notes']] = n
            while '  ' in row[H['project_name']]:
                row[H['project_name']] = row[H['project_name']].replace('  ', ' ')
            patched += 1
            print(f'[patch] {bid} streaming={pr["cfg"]} ({pr["cfg_dt"]}s) '
                  f'main={"yes" if pr["main"] else "no "} '
                  f'm3u8={pr["m3u8"]["status"]} live={live}')
            time.sleep(0.3)

        tmp = CSV_PATH + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
            for r in rows:
                w.writerow(r)
        os.replace(tmp, CSV_PATH)
        print(f'[done] patched {patched} rows')
    finally:
        try:
            os.close(lock_fd)
        except OSError:
            pass
        try:
            os.remove(CSV_PATH + '.lock')
        except OSError:
            pass


if __name__ == '__main__':
    main()
