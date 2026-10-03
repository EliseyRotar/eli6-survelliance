"""
argus_cleanup_v4.py — clean ALL generic cam names, not just argus.

Pattern improvements over v3:
- Recognizes more URL patterns for cam IDs:
  /public-camera-data/Axis-Name1/latest-frame.jpg -> "Axis-Name1"
  /cam_images/cam123.jpg -> "cam123"
  /view/1234.jpg -> "1234"
  /stream/chan-123_h -> "chan-123"
- Generates unique-ish names per cam (operator + extracted ID)
- Doesn't duplicate operator name across all cams
"""
import csv
import re
from pathlib import Path

CSV_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')

HOST_OPERATOR = {
    'cameras.alertcalifornia.org': 'ALERTCalifornia',
    'images-webcams.windy.com': 'Windy Webcam',
    'imgproxy.windy.com': 'Windy Webcam',
    'webcams.opensnow.com': 'OpenSnow',
    'www.atv.jp': 'Japan ATV Weather',
    'cam.river.go.jp': 'Japan MLIT River',
    'etraffic.dgt.es': 'Spain DGT',
    'wzmedia.dot.ca.gov': 'Caltrans',
    'www.houstontranstar.org': 'Houston TranStar',
    'prod-ut.ibi511.com': 'NY 511',
    'www.nvroads.com': 'Nevada Roads',
    'tdcctv.data.one.gov.hk': 'Hong Kong TDCCTV',
    'video.dot.state.mn.us': 'Minnesota DOT',
    'video.auth1.iol.pt': 'Beachcam Portugal',
    'video.auth2.iol.pt': 'Beachcam Portugal',
    'video.auth3.iol.pt': 'Beachcam Portugal',
    'video.autostrade.it': 'Italy Autostrade',
    'atmsqf.iowadot.gov': 'Iowa DOT',
    'video1.iowadot.gov': 'Iowa DOT',
    'video2.iowadot.gov': 'Iowa DOT',
    'video3.iowadot.gov': 'Iowa DOT',
    'video4.iowadot.gov': 'Iowa DOT',
    'www.netraveldata.co.uk': 'UK NE Travel',
    'imageserver.webcamera.pl': 'Poland Webcamera',
    'weathercam.digitraffic.fi': 'Finland Digitraffic',
    'phenocam.nau.edu': 'NEON Phenocam',
    'www.511ny.org': 'NY 511',
    'informo.madrid.es': 'Madrid Informo',
    'i-traffic.co.za': 'i-Traffic South Africa',
    'micamerasimages.net': 'Micam Images',
    'cctv.jogjaprov.go.id': 'Jogjaprov Indonesia',
    'public.carsprogram.org': 'CARSPROGRAM',
    'wtvpict.feratel.com': 'Feratel',
    'wtvthmb.feratel.com': 'Feratel',
    'map.bayerninfo.de': 'Bayern Info',
    '511on.ca': 'Ontario 511',
    'www.newengland511.org': 'New England 511',
    'cctv.divvysign.com': 'DivvySign',
    'vibes.dot.ca.gov': 'Caltrans Vibes',
    'www.skylinewebcams.com': 'Skyline Webcams',
    'video.kamere.com': 'Kamere',
    'api.wetcentrally.com': 'WetCentrally',
    '62.169.56.50': 'Italian IP Cam',
    'cam.creme.io': 'Creme.io',
    'vdo.telecores.com': 'Telecores',
    'cdn.openuni.io': 'OpenUni',
    'livecam.dandenong.vic.gov.au': 'Dandenong Live',
    'rivercam.niwa.co.nz': 'NIWA Rivercam',
    'mountainwatch.com': 'Mountain Watch',
    'rthkweb.mediahosting.app': 'RTHK',
    'snow.cusalpin.eu': 'Cusalpin Snow',
    'api.yr.no': 'YR Weather',
    'media-cdn.mgm-corp.com': 'MGM Corp',
}

GENERIC_PATTERNS = [
    re.compile(r'^[a-z0-9-]+\s+webcam$', re.I),
    re.compile(r'^[a-z0-9-]+\s+camera$', re.I),
    re.compile(r'^cameras?\s+webcam$', re.I),
    re.compile(r'^videos?\s+webcam$', re.I),
    re.compile(r'^cam[_a-z0-9-]+$', re.I),
    re.compile(r'^cctv[_a-z0-9-]*$', re.I),
    re.compile(r'^https?:', re.I),
    re.compile(r'^\d+\.jpg$', re.I),
    re.compile(r'\.m3u8$', re.I),
    re.compile(r'^rtsp:', re.I),
]

# More comprehensive ID extraction patterns. Order matters — most specific first.
ID_PATTERNS = [
    # Most specific patterns first
    r'/public-camera-data/([A-Za-z][A-Za-z0-9_-]+?)/latest',
    r'/public-camera-data/([A-Za-z][A-Za-z0-9_-]+?)/',
    r'/Axis[-_]([A-Za-z0-9][A-Za-z0-9_-]+)',
    r'/Public/RestAreas/([A-Z][A-Z0-9-]+)',     # Iowa DOT
    r'/Public/(?:Highways|Intersections|Ramps|Cameras)/([A-Z][A-Z0-9-]+)',
    r'/video-frames/(dt\d+/[0-9a-f]{8})',       # Italy Autostrade: dt7/a3c36eb0
    r'/video-frames/(dt\d+)',
    r'/snapshots/Public/\w+/([A-Z][A-Z0-9-]+)',
    r'/map/Cctv/(\d+)',                          # Nevada Roads
    r'/cctv/(\d+)',
    r'/webcam/([A-Za-z0-9-]+)',
    r'/images/([A-Z][A-Z0-9_-]+?)\.',
    r'/cam[-_]([A-Za-z0-9][A-Za-z0-9_-]+?)\.',
    r'/chan[-_](\w+)/',
    r'/chan[-_](\w+)\.',
    r'cctv[-_](\d+)\.',
    r'cam[_=](\d+)',
    r'cam[-_](\d+)\.jpg',
    r'camera[-_](\d+)\.',
    r'/(\d+)/image\.jpg',
    r'/(\d+)/latest\.jpg',
    r'/(\d{4,})\.jpg',
    r'images/(\d+)\.jpg',
    r'live/(\d{4,})',
    r'/cam[_-]?(\d+)',
    r'idx[=](\d+)',
    r'/([A-Z0-9]{2,}[_-][A-Z][_-]?\d+)\.jpg',
    r'/([A-Z]\d+_?[A-Z]?_\d+)\.jpg',
]


def operator_from_host(host):
    if not host:
        return ''
    host = host.lower()
    if host in HOST_OPERATOR:
        return HOST_OPERATOR[host]
    base = re.sub(r'^www\.', '', host)
    parts = base.split('.')
    if len(parts) >= 2:
        sub = parts[0]
        if sub in ('cam', 'cams', 'video', 'image', 'images', 'cctv', 'snapshot', 'www'):
            sub = parts[1] if len(parts) > 1 else sub
        sub = re.sub(r'\.(com|net|org|gov|io|eu|co\.uk)$', '', sub)
        return sub.title()
    return ''


def is_generic(name):
    if not name:
        return True
    n = name.strip()
    if len(n) < 4:
        return True
    for pat in GENERIC_PATTERNS:
        if pat.match(n):
            return True
    return False


def extract_cam_id(url):
    if not url:
        return None
    for pat in ID_PATTERNS:
        m = re.search(pat, url, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def main():
    print(f'Reading {CSV_PATH}')
    with open(CSV_PATH, encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    header = rows[0]
    data = rows[1:]
    H = {k: i for i, k in enumerate(header)}

    updated = 0
    sample = []
    for row in data:
        if len(row) != len(header):
            continue
        name = row[H['project_name']] if H['project_name'] < len(row) else ''
        if not is_generic(name):
            continue
        host = row[H['host']] if H['host'] < len(row) else ''
        url = row[H['url']] if H['url'] < len(row) else ''
        live = row[H['live_stream_url']] if H['live_stream_url'] < len(row) else ''

        operator = operator_from_host(host)
        if not operator:
            continue
        cam_id = extract_cam_id(url) or extract_cam_id(live)
        new_name = f'{operator} Cam {cam_id}' if cam_id else operator

        if new_name == name:
            continue
        if len(new_name) > 120:
            new_name = new_name[:117] + '...'

        row[H['project_name']] = new_name
        notes_idx = H.get('notes', -1)
        if notes_idx >= 0:
            existing_notes = row[notes_idx] if notes_idx < len(row) else ''
            tag = 'argus_cleanup_v4'
            if tag not in existing_notes:
                row[notes_idx] = (existing_notes + ' ' + tag).strip()[:200]
        updated += 1
        if len(sample) < 25:
            idx_val = row[H['idx']] if H['idx'] < len(row) else '?'
            sample.append((idx_val, name, new_name))

    print(f'Updating {updated} generic names')
    if sample:
        print('\nSample changes:')
        for idx, old, new in sample:
            print(f'  idx={idx}: "{old}" -> "{new}"')

    if not updated:
        return

    print(f'\nWriting back to {CSV_PATH}')
    with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(header)
        for row in data:
            writer.writerow(row)
    print('Done.')


if __name__ == '__main__':
    main()
