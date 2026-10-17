"""Session 47 CSV fix pass — DGT live-status refresh + rectify mislabeled rows.

1. DGT liveness refresh (census 2026-10-17): all 1,933 rows whose image is
   camarasEtraffic/{id}.jpg get http_status from census; 21 newly-404 rows get
   live_status='' and an image-404@2026-10-17 note.
2. Rectify rows whose metadata is wrong (OpenCCTV/argus-v2 disc_ rows carried
   garbled names, foreign coordinates e.g. 'Grimbergen, Spain' lat 50.95, and
   category=public): overwrite name/country/region/city/road/coords/category/
   likely_subject from the official sources used in Session 47 (DGT eTraffic API
   + DATEX2 provinces, opendata.euskadi.eus, gencat WFS, mobilitat.ad,
   camarasdgt/YouTube). Trigger: name contains ' · ' pattern OR country mismatch
   OR coords missing/>0.2deg off official.

Single csv lock; idempotent (notes marker 'rectified-20261017').

Usage: python -X utf8 scripts/fix/es47_refresh_rectify.py
"""
import csv
import json
import math
import os
import re
import sys
import time
import unicodedata
from urllib.parse import urlparse

ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
CAM = os.path.join(ROOT, 'camera_testing')
CSV_PATH = os.path.join(ROOT, 'controllable_Webcams.csv')
INV_PATH = os.path.join(CAM, '_es_inventory.json')
CEN_PATH = os.path.join(CAM, '_es_census.json')

INE = {"1": "Álava", "2": "Albacete", "3": "Alicante", "4": "Almería", "5": "Ávila",
       "6": "Badajoz", "7": "Illes Balears", "8": "Barcelona", "9": "Burgos", "10": "Cáceres",
       "11": "Cádiz", "12": "Castellón", "13": "Ciudad Real", "14": "Córdoba", "15": "A Coruña",
       "16": "Cuenca", "17": "Girona", "18": "Granada", "19": "Guadalajara", "20": "Huelva",
       "21": "Huesca", "22": "Jaén", "23": "León", "24": "Lleida", "25": "La Rioja", "26": "Lugo",
       "27": "Madrid", "28": "Málaga", "29": "Murcia", "30": "Navarra", "31": "Ourense",
       "32": "Asturias", "33": "Palencia", "34": "Las Palmas", "35": "Pontevedra",
       "36": "Salamanca", "37": "S.C. Tenerife", "38": "Cantabria", "39": "Segovia",
       "40": "Sevilla", "41": "Soria", "42": "Tarragona", "43": "Teruel", "44": "Toledo",
       "45": "Valencia", "46": "Valladolid", "47": "Bizkaia", "48": "Zamora", "49": "Zaragoza",
       "50": "Ceuta", "51": "Melilla"}


def ascii_s(s):
    return unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode('ascii')


def fnum(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).strip().replace(',', '.'))
    except ValueError:
        return None


def jload(n):
    return json.load(open(os.path.join(CAM, n), encoding='utf-8'))


def dist_km(lat1, lon1, lat2, lon2):
    try:
        lat1, lon1, lat2, lon2 = map(float, (lat1, lon1, lat2, lon2))
    except Exception:
        return 999.0
    dy = (lat1 - lat2) * 111.0
    dx = (lon1 - lon2) * 111.0 * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(dx, dy)


def build_datex_prov():
    prov = {}
    xml = open(os.path.join(CAM, '_es_datex2_v37.xml'), encoding='utf-8', errors='replace').read()
    for blk in re.split(r'<ns2:device\b', xml)[1:]:
        m_id = re.search(r'id="(\d+)"', blk)
        if not m_id:
            continue
        m = re.search(r'<lse:province>([^<]+)</lse:province>', blk)
        if m:
            prov[m_id.group(1)] = m.group(1).strip().title()
    return prov


def build_dgt_meta():
    datex_prov = build_datex_prov()
    meta = {}

    def put(did, road, pk, sentido, lat, lon, region):
        name = ''
        if road:
            name = f'{road} km {pk}' if pk not in (None, '') else road
            if sentido:
                name += f' {sentido}'
        meta[did] = {'name': name, 'road': road or '', 'lat': lat, 'lon': lon,
                     'region': region or ''}

    prod = {c['idCamara']: c for c in jload('_es_camaras_etraffic.json')['camaras']}
    for did, c in prod.items():
        put(did, c.get('carretera'), c.get('pk'), c.get('sentido'),
            c.get('coordY'), c.get('coordX'), datex_prov.get(did, ''))
    pre = {c['idCamara']: c for c in jload('_es_camaras_pre.json')['camaras']}
    for did, c in pre.items():
        if did not in meta:
            put(did, c.get('carretera'), c.get('pk'), c.get('sentido'),
                c.get('coordY'), c.get('coordX'), datex_prov.get(did, ''))
    for c in jload('_es_camaras_dgt.json')['camaras']:
        did = c.get('id')
        if did in meta:
            continue
        lat, lon = fnum(c.get('latitud')), fnum(c.get('longitud'))
        if lat is not None and lat < 0:
            lat = abs(lat)
        region = datex_prov.get(did) or INE.get(str(c.get('provincia') or '').strip(), '')
        put(did, c.get('carretera'), c.get('pk'), c.get('sentido'), lat, lon, region)
    return meta


def build_inv_maps():
    inv = jload('_es_inventory.json')
    # same cleanup as finalize
    for e in inv:
        if e['key'] == 'cat-5':
            e['image_url'] = e['image_url'].replace(' &#13;', '').strip()
        if e['key'] == 'eusk-127':
            e['image_url'] = e['image_url'].replace('127 .jpg', '127.jpg')
    id_maps = {'eusk': {}, 'cat': {}, 'ando': {}, 'vit': {}, 'web': {}}
    url_map = {}
    for e in inv:
        u = e['image_url']
        url_map[u.replace('https://', 'http://')] = e
        p = e['prefix']
        if p == 'eusk':
            m = re.search(r'camaras/(\d+)\s*\.jpg', u)
            if m:
                id_maps['eusk'][m.group(1)] = e
        elif p == 'cat':
            m = re.search(r'sctidcam=([\w.-]+?)(?:\.gif|\.jpg)?$', u)
            if m:
                id_maps['cat'][m.group(1).rstrip('.').lower()] = e
            m = re.search(r'TransitCamera\?nom=([\w.-]+?)(?:\.gif|\.jpg)?$', u)
            if m:
                id_maps['cat'][m.group(1).rstrip('.').lower()] = e
        elif p == 'ando':
            m = re.search(r'prod/([\w.-]+)\.gif', u)
            if m:
                id_maps['ando'][m.group(1).lower()] = e
        elif p == 'vit':
            m = re.search(r'id=([\w_]+)', u)
            if m:
                id_maps['vit'][m.group(1)] = e
        elif p == 'web':
            m = re.search(r'watch\?v=([\w-]+)', e.get('stream_url', ''))
            if m:
                id_maps['web'][m.group(1)] = e
    return inv, id_maps, url_map


def main():
    csv.field_size_limit(10**7)
    dgt_meta = build_dgt_meta()
    inv, id_maps, url_map = build_inv_maps()
    cen = json.load(open(CEN_PATH, encoding='utf-8'))
    dgt_status = cen['dgt_refresh']  # idx(str) -> {csv_id,id,status,lm}

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

    stats = {'refresh': 0, 'dead': 0, 'rect_dgt': 0, 'rect_inv': 0, 'changed_cells': 0}
    try:
        with open(CSV_PATH, encoding='utf-8', newline='') as f:
            rows = list(csv.reader(f))
        header = rows[0]
        H = {name: i for i, name in enumerate(header)}
        for r in rows[1:]:
            idx = r[H['idx']] if len(r) > H['idx'] else ''
            joined = ' '.join((r[H['live_stream_url']] or '', r[H['url']] or ''))
            changed = []

            def setc(name, val, force=False):
                i = H[name]
                if val is None or val == '':
                    return
                if force or (r[i] or '') != val:
                    if r[i] != val:
                        changed.append(name)
                    r[i] = val

            # ---- 1) DGT liveness refresh ----
            m = re.search(r'camarasEtraffic/(\d+)\.jpg', joined)
            if m and 'dgt.es' in joined:
                sv = dgt_status.get(idx)
                if sv:
                    st = sv.get('status')
                    setc('http_status', str(st) if st is not None else '')
                    stats['refresh'] += 1
                    if st != 200:
                        if r[H['live_status']] == 'live':
                            r[H['live_status']] = ''
                            changed.append('live_status')
                        if 'image-404@2026-10-17' not in (r[H['notes']] or ''):
                            r[H['notes']] = (r[H['notes']] or '') + '; image-404@2026-10-17'
                            changed.append('notes')
                        stats['dead'] += 1

            if 'rectified-20261017' in (r[H['notes']] or ''):
                continue

            # ---- 2) rectification ----
            entry = None
            grp = None
            if m and 'dgt.es' in joined:
                did = m.group(1)
                dm = dgt_meta.get(did)
                if dm:
                    entry = {'name': dm['name'], 'country': 'Spain',
                             'region': dm['region'], 'city': '', 'road': dm['road'],
                             'lat': dm['lat'], 'lon': dm['lon'], 'category': 'traffic',
                             'geo_source': '', 'location_precision': 'precise'}
                    grp = 'dgt'
            if entry is None:
                # eusk (any host), by id
                m2 = re.search(r'trafikoa[\w.-]*/static/files/tr/camaras/(\d+)\s*\.jpg', joined)
                if m2:
                    entry = id_maps['eusk'].get(m2.group(1))
                    grp = 'eusk'
                if entry is None:
                    m2 = re.search(r'sctidcam=([\w.-]+?)(?:\.gif|\.jpg)?(?:&|\s|$)', joined) or \
                         re.search(r'TransitCamera\?nom=([\w.-]+?)(?:\.gif|\.jpg)?(?:&|\s|$)', joined)
                    if m2:
                        entry = id_maps['cat'].get(m2.group(1).rstrip('.').lower())
                        grp = 'cat'
                if entry is None:
                    m2 = re.search(r'imgs\.mobilitat\.ad/prod/([\w.-]+)\.gif', joined)
                    if m2:
                        entry = id_maps['ando'].get(m2.group(1).lower())
                        grp = 'ando'
                if entry is None:
                    m2 = re.search(r'vitoria-gasteiz\.org/[^ ]*id=([\w_]+)', joined)
                    if m2:
                        entry = id_maps['vit'].get(m2.group(1))
                        grp = 'vit'
                if entry is None:
                    m2 = re.search(r'watch\?v=([\w-]+)', joined)
                    if m2:
                        entry = id_maps['web'].get(m2.group(1))
                        grp = 'web'
                if entry is None:
                    for part in (r[H['live_stream_url']], r[H['url']]):
                        if part:
                            entry = url_map.get(part.replace('https://', 'http://'))
                            if entry is not None:
                                grp = entry['prefix']
                                break

            if entry is None:
                if changed:
                    stats['changed_cells'] += len(changed)
                continue

            name = entry.get('name') or ''
            country = entry.get('country') or ''
            elat, elon = entry.get('lat'), entry.get('lon')
            row_name = r[H['project_name']] or ''
            row_country = r[H['country']] or ''
            row_lat, row_lon = r[H['lat']], r[H['lon']]
            needs = False
            if ' · ' in row_name:
                needs = True
            if country and row_country and row_country != country:
                needs = True
            if elat is not None and elon is not None:
                if not row_lat or not row_lon:
                    needs = True
                elif dist_km(row_lat, row_lon, elat, elon) > 22.0:
                    needs = True
            if not needs:
                if changed:
                    stats['changed_cells'] += len(changed)
                continue

            # apply
            if name:
                setc('project_name', ascii_s(name))
            if country and row_country != country:
                setc('country', country)
            reg = entry.get('region') or ''
            if reg:
                setc('region', ascii_s(reg))
            elif r[H['region']] not in ('', 'Spain', 'Andorra'):
                r[H['region']] = ''
                changed.append('region')
            if entry.get('city'):
                setc('city', ascii_s(entry['city']))
            if entry.get('road'):
                setc('road', entry['road'])
            if elat is not None:
                setc('lat', str(elat), force=True)
            if elon is not None:
                setc('lon', str(elon), force=True)
            if entry.get('location_precision') and not r[H['location_precision']]:
                setc('location_precision', entry['location_precision'])
            if entry.get('geo_source') and not r[H['geo_source']]:
                setc('geo_source', entry['geo_source'])
            if entry.get('category') == 'traffic' and r[H['category']] != 'traffic':
                setc('category', 'traffic')
            if grp in ('dgt', 'eusk', 'cat') and entry.get('road'):
                subj = f"Traffic camera on {entry['road']}"
                near = entry.get('city') or entry.get('region') or ''
                if near:
                    subj += f' near {near}'
                setc('likely_subject', ascii_s(subj))
            r[H['notes']] = (r[H['notes']] or '') + '; rectified-20261017-from-official-source'
            changed.append('notes')
            if grp == 'dgt':
                stats['rect_dgt'] += 1
            else:
                stats['rect_inv'] += 1
            stats['changed_cells'] += len(changed)

        tmp = CSV_PATH + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
            for row in rows:
                w.writerow(row)
        os.replace(tmp, CSV_PATH)
    finally:
        try:
            os.close(lock_fd)
        except OSError:
            pass
        try:
            os.remove(CSV_PATH + '.lock')
        except OSError:
            pass
    print('[stats]', json.dumps(stats))
    print('[done] rows processed:', len(rows) - 1)


if __name__ == '__main__':
    main()
