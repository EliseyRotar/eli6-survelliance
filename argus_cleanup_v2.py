"""
Argus cleanup v2: better name enrichment from URL patterns.

For each argus cam, look at the URL to extract:
- Cam name (often embedded in path)
- City/location (from path or query string)
"""
import csv
import re
from pathlib import Path
from collections import Counter

CSV_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')

print("Reading CSV...")
with open(CSV_PATH, encoding='utf-8', newline='') as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = list(reader)
H = {k: i for i, k in enumerate(header)}

# URL patterns that reveal cam names
URL_PATTERNS = [
    # Specific operator patterns
    (r'/(\d+)/image\.jpg$', 'Cam {0}'),
    (r'/(\d+)\.jpg$', 'Cam {0}'),
    (r'/(?:cam|image|webcam|video|stream)/([A-Za-z0-9_-]+)\.jpg', 'Cam {0}'),
    # Travelmidwest IL (already known)
    (r'cctv\.travelmidwest\.com/snapshots/([A-Z]+-[A-Z0-9_]+_?[A-Z]?)\.jpg', 'IL Travelmidwest {0}'),
    # New York 511
    (r'/map/Cctv/(\d+)$', 'NY 511 Cam {0}'),
    # Iowa DOT - IICTV city code
    (r'video\d?\.iowadot\.gov:8888/(\w+)/(\w+)/', 'Iowa DOT {0} {1}'),
    # Caltrans district cams
    (r'wzmedia\.dot\.ca\.gov/D(\d+)/([A-Z]\d+)_([A-Z]+)_(\d+)_([A-Z]+_?[A-Z]?)\.stream', 'Caltrans D{0} Hwy {1} {3}'),
    # ccctv-info
    (r'cctv\.5giq\.com/(\w+)\.jpg', '5giQ {0}'),
    # Washington DOT
    (r'images\.wsdot\.wa\.gov/orflow/(\d+)\.jpg', 'WSDOT {0}'),
    # ALERTCalifornia
    (r'public-camera-data/(Axis-\w+?)(?:\d+)/latest-frame', 'ALERTCalifornia {0}'),
    # CalTrans KCO
    (r'cctv-ss(\d+)\.thb\.gov\.tw:443/(.+)', 'Taiwan Freeway {0} {1}'),
    # Generic Windy
    (r'imgproxy\.windy\.com/_/full/plain/current/(\d+)/original\.jpg', 'Windy Webcam {0}'),
    # Windy provider names from hostname
    (r'webcams\.windy\.com/[^/]+/(\w+)\.jpg', 'Windy {0}'),
    # Generic format from URL path
    (r'/(\w+)/image\.jpg', '{0} Cam'),
    (r'/(\w+)\.jpg', '{0}'),
    (r'/(\w+)/(\w+)\.jpg', '{0} {1}'),
    # tmts.tv traffic
    (r'tmts\.tv/\?channel=([\w-]+)', 'Taiwan TMT {0}'),
]

# Host name prefixes for fallback
HOST_NAME = {
    'cctv.travelmidwest.com': 'IL Travelmidwest',
    '511.alaska.gov': 'Alaska DOT',
    'video2.iowadot.gov': 'Iowa DOT',
    'video3.iowadot.gov': 'Iowa DOT',
    'video4.iowadot.gov': 'Iowa DOT',
    'atmsqf.iowadot.gov': 'Iowa DOT',
    'imgproxy.windy.com': 'Windy Webcam',
    'images-webcams.windy.com': 'Windy Webcam',
    'cctv.tomtomcdn.com': 'TomTom Cam',
    'cctv-ss01.thb.gov.tw': 'Taiwan Freeway',
    'cctv-ss02.thb.gov.tw': 'Taiwan Freeway',
    'cctv-ss03.thb.gov.tw': 'Taiwan Freeway',
    'cctv-ss04.thb.gov.tw': 'Taiwan Freeway',
    'cctv-ss05.thb.gov.tw': 'Taiwan Freeway',
    'cctv-ss06.thb.gov.tw': 'Taiwan Freeway',
    'cctv-ss07.thb.gov.tw': 'Taiwan Freeway',
    'cctv-ss08.thb.gov.tw': 'Taiwan Freeway',
    'cctv-ss09.thb.gov.tw': 'Taiwan Freeway',
    'cctv-ss10.thb.gov.tw': 'Taiwan Freeway',
    'cctvs.freeway.gov.tw': 'Taiwan Freeway',
    'cctvc.freeway.gov.tw': 'Taiwan Freeway',
    'wzmedia.dot.ca.gov': 'Caltrans',
    'cameras.alertcalifornia.org': 'ALERTCalifornia',
    'images.wsdot.wa.gov': 'WSDOT',
    'tmts.tv': 'Taiwan TMT',
    'stream.gran-canaria.com': 'Gran Canaria',
    'm.hak.hr': 'HAK Croatia',
    'webcams.aeroclubea.com': 'Aeroclube',
    'image.trabucocam.com': 'Trabuco Cam',
    'www.skylinewebcams.com': 'Skyline Webcam',
    '511ny.org': 'NY 511',
    'www.az511.com': 'AZ 511',
    '511pa.com': 'PA 511',
    '511.alaska.gov': 'Alaska DOT',
    'kenyawebcam.com': 'Kenya Webcam',
    'kenyawebcams.com': 'Kenya Webcams',
    'satapweb.it': 'SATAP Italy',
    's52.nysdot.skyvdn.com': 'NYSDOT Skyline',
    's51.nysdot.skyvdn.com': 'NYSDOT Skyline',
    's7.nysdot.skyvdn.com': 'NYSDOT Skyline',
    's9.nysdot.skyvdn.com': 'NYSDOT Skyline',
    's53.nysdot.skyvdn.com': 'NYSDOT Skyline',
    'www.drv.ee': 'Estonia Road',
    'teejuht.ee': 'Estonia Traffic',
    'wink.njta.com': 'NJ Turnpike',
    'www.511nj.org': 'NJ 511',
    'media-sfs1.vdotcameras.com': 'VA DOT',
    'media-sfs2.vdotcameras.com': 'VA DOT',
    'media-sfs3.vdotcameras.com': 'VA DOT',
    'media-sfs4.vdotcameras.com': 'VA DOT',
    'media-sfs5.vdotcameras.com': 'VA DOT',
    'media-sfs6.vdotcameras.com': 'VA DOT',
    'media-sfs7.vdotcameras.com': 'VA DOT',
    'media-sfs8.vdotcameras.com': 'VA DOT',
    'topiscctv1.eseoul.go.kr': 'Seoul TOPIS',
    'cctv.5giq.com': '5giQ Beijing',
    'video-auth1.iol.pt': 'Beachcam Portugal',
    'webcam-iss.hyperlounge.com': 'ISS Webcam',
    'view.atlanticcam.it': 'Atlantic Cam',
    'cam.vorndran.de': 'German Webcam',
    'images.webcamgalore.com': 'Webcamgalore',
    'webcam.spectra.net': 'Spectra Webcam',
    'c1.webcamtoo.com': 'Webcamtoo',
    'image.feratel.com': 'Feratel',
    'wtvpict.feratel.com': 'Feratel',
    'www.panomax.com': 'Panomax',
    'webcams.travelpayouts.com': 'Travelpayouts',
    'wpc.panoramio.com': 'Panoramio',
    'www.webcams.travel': 'Webcams.travel',
    'www.opentopia.com': 'Opentopia',
    'webcams.opentopia.com': 'Opentopia',
    'earthcam.com': 'EarthCam',
    'skylinewebcams.com': 'Skyline',
    'cdn.livespotting.com': 'Livespotting',
    'izmit.bel.tr': 'Kocaeli Turkey',
    'mugla.gov.tr': 'Mugla Turkey',
    'kayserimobese.gov.tr': 'Kayseri Turkey',
    'cam.river.go.jp': 'Japan MLIT',
    'shishi.city': 'Shishi City',
    'haisevision.com': 'Haise Vision',
    'skyline-dnshls.com': 'Skyline HLS',
    'webcams.org': 'Webcams.org',
    'weatherbug.com': 'WeatherBug',
    'hazcams.com': 'Hazcams',
    'citrixonline.com': 'Citrix',
    'webcambonus.com': 'Webcam Bonus',
    'appglu.com': 'AppG',
    'earthcam.net': 'EarthCam',
    'iitm.ac.in': 'IIT Madras',
    'iitb.ac.in': 'IIT Bombay',
    'fc.upc.edu': 'UPC Spain',
    'opendatacam.appspot.com': 'OpenDataCam',
    'meadowlark.com': 'Meadowlark',
    'airportview.net': 'Airport View',
    'webcamsdemexico.com': 'Mexico Webcams',
    'mx.camdiscovery.com': 'Mexico Cam',
    'webcamschina.com': 'China Webcams',
    'livecam24.com': 'LiveCam24',
    'skyline.software': 'Skyline',
    'webcam4u.com': 'Webcam4u',
    'webcamsweden.com': 'Sweden Webcams',
    'trafiken.nu': 'Sweden Trafiken',
    'nwt.se': 'NWT',
    'trafikinfo.se': 'Trafikinfo',
    'webbkameror.se': 'Webbkameror',
    'www.svt.se': 'SVT',
    'webkameror.no': 'Webkameror Norge',
    'www.vegvesen.no': 'Norwegian Roads',
    'webcamsdenmark.dk': 'Denmark Webcams',
    'www.dmi.dk': 'DMI Denmark',
    'dumpr.nl': 'DumpRender',
}

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

# Process each
updated = 0
for ri, row in argus:
    name = row[H['project_name']]
    if len(name) >= 30:  # already a good name
        continue
    live = row[H['live_stream_url']] if len(row) > H['live_stream_url'] else ''
    url = row[H['url']] if len(row) > H['url'] else ''
    host = row[H['host']] if len(row) > H['host'] else ''

    new_name = None
    for pattern, replacement in URL_PATTERNS:
        m = re.search(pattern, live or url)
        if m:
            try:
                new_name = re.sub(pattern, replacement, live or url)
                new_name = re.sub(r'[^A-Za-z0-9\s\-_:.]+', ' ', new_name).strip()[:120]
            except:
                new_name = None
            if new_name and len(new_name) > len(name):
                break

    if not new_name or len(new_name) < 5:
        # Use host name as fallback
        host_clean = host.replace('www.', '').replace('http://', '').replace('https://', '')
        if host_clean in HOST_NAME:
            new_name = HOST_NAME[host_clean]
        else:
            new_name = f"{host_clean} Webcam"

    if new_name and new_name != name:
        row[H['project_name']] = new_name
        updated += 1

print(f"Updated {updated} argus names")

# Write back
with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
print("Saved.")
