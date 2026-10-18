"""Session-47c: dedupe the 25 bcn.cat transit cameras (disc_ junk-name vs tv_ proper).

www.bcn.cat/transit/imatges/<Key>.gif cameras exist twice in CSV:
  - 24 pairs: disc_173xx rows (argus gazetteer names like 'Les Mureaux,
    Ile-de-France - Bcn') + tv_1396xx rows (trafficvision proper names, good
    coords). Same gif path -> drop the disc_ keeper of each pair (tv_ wins).
  - disc_17301 PlCerda: disc-only -> renamed 'Placa de Cerda', kept.
  - tv_139634 TunelRovira: tv-only, already proper.

All 25 gifs probed live 2026-10-17 (http->https redirect, image/gif).
Posters: fetch gif -> PIL -> web_viewer/static/posters/{idx}.jpg.

Usage: python -X utf8 camera_testing/_es_bcn_fix.py
"""
import csv
import io
import json
import os
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image

ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
CSV_PATH = os.path.join(ROOT, 'controllable_Webcams.csv')
STATE_PATH = os.path.join(ROOT, 'camera_testing', 'es_bcn_fix_state.json')
POSTER_DIR = os.path.join(ROOT, 'web_viewer', 'static', 'posters')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
TAG = 'name-fix-from-gif@20261017'


def gif_key(u):
    m = re.search(r'imatges/([A-Za-z0-9]+)\.gif', u or '')
    return m.group(1) if m else None


def fetch_poster(idx, url):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=25) as r:
            body = r.read(524288)
        if len(body) < 1000:
            return idx, f'small:{len(body)}'
        im = Image.open(io.BytesIO(body))
        im = im.convert('RGB')
        dst = os.path.join(POSTER_DIR, f'{idx}.jpg')
        im.save(dst, 'JPEG', quality=82)
        return idx, 'ok'
    except Exception as e:
        return idx, f'fail:{type(e).__name__}:{e}'


def main():
    lock = CSV_PATH + '.lock'
    for a in range(80):
        try:
            os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            break
        except FileExistsError:
            time.sleep(0.05)
    else:
        sys.exit('[fatal] lock')
    stats = {'dropped_disc': [], 'renamed': [], 'probed': []}
    try:
        with open(CSV_PATH, newline='', encoding='utf-8') as f:
            rd = csv.DictReader(f)
            cols = rd.fieldnames
            rows = list(rd)
        by_key = {}
        for r in rows:
            cid = r['csv_id'] or ''
            u = r['live_stream_url'] or r['url'] or ''
            if 'bcn.cat/transit/imatges' in u:
                k = gif_key(u)
                if k:
                    by_key.setdefault(k, {})[cid.split('_')[0]] = r
        drop_idxs = set()
        keep_rows = []  # (idx, url) for probing/posters
        for k, sides in sorted(by_key.items()):
            disc, tv = sides.get('disc'), sides.get('tv')
            if disc and tv:
                drop_idxs.add(disc['idx'])
                stats['dropped_disc'].append((disc['csv_id'], k))
                keep_rows.append((tv['idx'], tv['live_stream_url'] or tv['url']))
            elif disc and not tv:
                disc['project_name'] = 'Plaça de Cerdà'
                disc['description'] = 'Plaça de Cerdà'
                disc['org'] = 'Ajuntament de Barcelona (Transit)'
                disc['likely_subject'] = 'City traffic camera (Plaça de Cerdà, Barcelona)'
                if TAG not in (disc['notes'] or ''):
                    disc['notes'] = ((disc['notes'] + '; ') if disc['notes'] else '') + TAG
                stats['renamed'].append((disc['csv_id'], k))
                keep_rows.append((disc['idx'], disc['live_stream_url'] or disc['url']))
            elif tv:
                keep_rows.append((tv['idx'], tv['live_stream_url'] or tv['url']))
        rows = [r for r in rows if r['idx'] not in drop_idxs]
        # drop orphaned posters of removed rows
        for i in drop_idxs:
            p = os.path.join(POSTER_DIR, f'{i}.jpg')
            if os.path.exists(p):
                os.remove(p)
        tmp = CSV_PATH + '.tmp'
        with open(tmp, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=cols, lineterminator='\n')
            w.writeheader()
            w.writerows(rows)
        os.replace(tmp, CSV_PATH)
    finally:
        if os.path.exists(lock):
            os.remove(lock)
    print(f"[csv] dropped_disc={len(stats['dropped_disc'])} renamed={stats['renamed']} kept={len(keep_rows)}")
    res = {}
    with ThreadPoolExecutor(6) as ex:
        futs = {ex.submit(fetch_poster, idx, url): idx for idx, url in keep_rows}
        for fut in as_completed(futs):
            idx, st = fut.result()
            res[idx] = st
    ok = sum(1 for v in res.values() if v == 'ok')
    print(f'[posters] ok={ok} fail={len(res) - ok} of {len(keep_rows)}')
    fails = {k: v for k, v in res.items() if v != 'ok'}
    if fails:
        print('[fails]', fails)
    json.dump({'stats': stats, 'posters': res}, open(STATE_PATH, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
