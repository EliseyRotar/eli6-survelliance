"""Session-47c small fixes: Sóller geocode, gotafreda death, Morocco country, IPTV de-junk.

  disc_42996  Club Nautic Soller webcam: junk Norfolk-Virginia geocode ->
              official club coords 39.7972155, 2.6922431 (nominatim Club Nautic,
              Port de Soller). Image confirmed live 2026-10-17 (85 KB jpeg).
  disc_201367 gotafreda.es estacio c23m145e12: host dead (https TLS fail, http
              301->https); unidentified location (no OSM/Nominatim hit) -> dead
              mark, coords/region cleared.
  tv_121105   Banana Beach (in2thebeach.es stream): camera is in Agadir region,
              Morocco -> country Spain -> Morocco.
  ~14 rows    Spanish IPTV channel streams (*/canal_*/index.m3u8 on eivotv/strei
              hosts) with foreign gazetteer names+coords -> neutral names, coords
              cleared, flagged non-camera.

Usage: python -X utf8 camera_testing/_es_smallfix.py
"""
import csv
import json
import os
import re
import sys
import time
import urllib.request

ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
CSV_PATH = os.path.join(ROOT, 'controllable_Webcams.csv')
STATE_PATH = os.path.join(ROOT, 'camera_testing', 'es_smallfix_state.json')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}


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
    stats = {'soller': 0, 'gata': 0, 'banana': 0, 'iptv': 0}
    iptv_ids = []
    try:
        with open(CSV_PATH, newline='', encoding='utf-8') as f:
            rd = csv.DictReader(f)
            cols = rd.fieldnames
            rows = list(rd)
        for r in rows:
            u = r['live_stream_url'] or r['url'] or ''
            blob = (r['url'] or '') + ' ' + (r['live_stream_url'] or '')
            if r['csv_id'] == 'disc_42996':
                r['project_name'] = 'Club Nàutic Sóller - Webcam HD'
                r['description'] = 'Club Nàutic Sóller - Webcam HD'
                r['lat'] = '39.7972155'
                r['lon'] = '2.6922431'
                r['geo_source'] = 'nominatim-poi'
                r['location_precision'] = 'precise'
                r['region'] = 'Balearic Islands'
                r['city'] = 'Port de Sóller'
                r['org'] = 'Club Nàutic Sóller'
                r['category'] = 'scenic'
                r['likely_subject'] = 'Marina/harbour webcam (Port de Sóller, Mallorca)'
                if 'geo-fix-20261017-soller-nautic' not in (r['notes'] or ''):
                    r['notes'] = ((r['notes'] + '; ') if r['notes'] else '') + 'geo-fix-20261017-soller-nautic'
                stats['soller'] += 1
            elif r['csv_id'] == 'disc_201367':
                r['project_name'] = 'Gotafreda webcam (estacio c23m145e12)'
                r['description'] = 'Gotafreda webcam (estacio c23m145e12)'
                r['lat'] = ''
                r['lon'] = ''
                r['geo_source'] = ''
                r['location_precision'] = 'no_geocode_result'
                r['region'] = ''
                r['city'] = ''
                r['org'] = ''
                r['live_status'] = ''
                r['http_status'] = ''
                r['likely_subject'] = 'Unidentified Spanish station webcam (host dead)'
                for tag in ('host-unreachable@2026-10-17', 'location-unknown@2026-10-17',
                            'argus-geocode-discarded@2026-10-17'):
                    if tag not in (r['notes'] or ''):
                        r['notes'] = ((r['notes'] + '; ') if r['notes'] else '') + tag
                stats['gata'] += 1
            elif r['csv_id'] == 'tv_121105':
                r['country'] = 'Morocco'
                if 'country-fix-to-morocco@2026-10-17' not in (r['notes'] or ''):
                    r['notes'] = ((r['notes'] + '; ') if r['notes'] else '') + 'country-fix-to-morocco@2026-10-17'
                stats['banana'] += 1
            elif r['country'] == 'Spain' and re.search(r'/canal_[A-Za-z0-9_]+/index\.m3u8', u):
                m = re.search(r'/canal_([A-Za-z0-9_]+)/', u)
                canal = 'canal_' + (m.group(1) if m else '?')
                r['project_name'] = f'IPTV stream {canal} (non-camera)'
                r['description'] = f'IPTV stream {canal} (non-camera)'
                r['lat'] = ''
                r['lon'] = ''
                r['geo_source'] = ''
                r['location_precision'] = 'no_geocode_result'
                r['region'] = ''
                r['city'] = ''
                r['likely_subject'] = 'IPTV live stream (not a webcam)'
                if 'non-camera-iptv-stream@2026-10-17' not in (r['notes'] or ''):
                    r['notes'] = ((r['notes'] + '; ') if r['notes'] else '') + 'non-camera-iptv-stream@2026-10-17'
                stats['iptv'] += 1
                iptv_ids.append(r['csv_id'])
        tmp = CSV_PATH + '.tmp'
        with open(tmp, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=cols, lineterminator='\n')
            w.writeheader()
            w.writerows(rows)
        os.replace(tmp, CSV_PATH)
    finally:
        if os.path.exists(lock):
            os.remove(lock)
    # re-probe soller image for http/live fields
    try:
        req = urllib.request.Request('http://www.clubnauticsoller.es/imag/webcamHD.jpg', headers=UA)
        with urllib.request.urlopen(req, timeout=25) as resp:
            body = resp.read(524288)
        soller_live = len(body) > 5000 and body[:2] == b'\xff\xd8'
    except Exception as e:
        soller_live = False
    json.dump({'stats': stats, 'iptv_ids': iptv_ids, 'soller_probe': 'live' if soller_live else 'fail'},
              open(STATE_PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'[done] {stats} soller_probe={"live" if soller_live else "fail"}')
    if soller_live:
        lock = CSV_PATH + '.lock'
        for a in range(80):
            try:
                os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                break
            except FileExistsError:
                time.sleep(0.05)
        else:
            sys.exit('[fatal] lock2')
        try:
            with open(CSV_PATH, newline='', encoding='utf-8') as f:
                rd = csv.DictReader(f)
                cols = rd.fieldnames
                rows = list(rd)
            for r in rows:
                if r['csv_id'] == 'disc_42996':
                    r['http_status'] = '200'
                    r['content_type'] = 'image/jpeg'
                    r['live_status'] = 'live'
            tmp = CSV_PATH + '.tmp'
            with open(tmp, 'w', newline='', encoding='utf-8') as f:
                w = csv.DictWriter(f, fieldnames=cols, lineterminator='\n')
                w.writeheader()
                w.writerows(rows)
            os.replace(tmp, CSV_PATH)
        finally:
            if os.path.exists(lock):
                os.remove(lock)


if __name__ == '__main__':
    main()
