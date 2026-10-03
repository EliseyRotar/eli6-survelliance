"""
Argus cleanup v3: clean up messy URL-derived names.

The v2 produced names like:
  'https: cameras.alertcalifornia.org ALERTCalifornia  0 .jpg'
  'https: www.nvroads.comNY 511 Cam  0'

We want clean names like:
  'ALERTCalifornia Cam 0'
  'Nevada Roads Cam 0'
"""
import csv
import re
from pathlib import Path

CSV_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')

print("Reading CSV...")
with open(CSV_PATH, encoding='utf-8', newline='') as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = list(reader)
H = {k: i for i, k in enumerate(header)}

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
}

# Pattern to find messy URL-derived names
URL_DERIV_PATTERNS = [
    r'https?:\s*\S+\s+',          # leading URL
    r'http[s]?:\s*',
    r'camarasEtrafficCam\s+',
    r'snapshots\s*cctv',
    r'latest\s*',
    r'currentCam\s*',
    r'\.jpg',
    r'nowCam\s*',
    r'\.m3u8',
    r'playlist\.m3u8',
]

# Find all argus rows
argus = []
for ri, row in enumerate(rows):
    if len(row) != len(header):
        continue
    notes = row[H['notes']] if len(row) > H['notes'] else ''
    if 'argus_cleanup_v1' not in notes:
        continue
    argus.append((ri, row))

print(f"Argus rows: {len(argus)}")

# Process
updated = 0
for ri, row in argus:
    name = row[H['project_name']]
    if not name or len(name) < 8:
        continue
    # Only clean messy URL-derived ones
    is_messy = 'https' in name.lower() or '.jpg' in name or '.m3u8' in name or ' playlist' in name or 'snapshots' in name
    if not is_messy:
        continue
    host = row[H['host']] if len(row) > H['host'] else ''
    url = row[H['url']] if len(row) > H['url'] else ''
    live = row[H['live_stream_url']] if len(row) > H['live_stream_url'] else ''

    # Find cam ID from URL
    cam_id = None
    for candidate in (live, url):
        # Patterns to extract IDs
        for pat in [
            r'/([A-Z0-9]{2,}[_-][A-Z][_-]?\d+)\.jpg',
            r'/([A-Z]\d+_?[A-Z]?_\d+)\.jpg',
            r'/(\d+)/image\.jpg',
            r'cam[_=](\d+)',
            r'cam[_-](\d+)\.jpg',
            r'camera[_-](\d+)\.',
            r'cctv[_-]?(\d+)\.jpg',
            r'images/(\d+)\.jpg',
            r'/(\d+)\.jpg',
        ]:
            m = re.search(pat, candidate, re.IGNORECASE)
            if m:
                cam_id = m.group(1)
                break
        if cam_id:
            break

    operator = HOST_OPERATOR.get(host, host.replace('www.', '').replace('.com', '').replace('.gov', '').title() or 'Cam')

    new_name = f"{operator}"
    if cam_id:
        new_name = f"{operator} Cam {cam_id}"

    if new_name and new_name != name:
        row[H['project_name']] = new_name
        updated += 1

print(f"Updated {updated} messy names")

# Write back
with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
print("Saved.")
