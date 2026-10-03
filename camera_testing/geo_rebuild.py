"""
geo_rebuild.py - Rebuild cam lat/lon/city/region/country by cross-checking sources.

Priority:
  1. TrafficVision catalog (148k cams, authoritative) — match by host + URL fragment
  2. TLD inference (.it → Italy, .jp → Japan, etc.)
  3. Hardcoded host → region map for known DOT/agency hosts
  4. Keep existing geo if reasonable (in same country as TLD or hardcoded)
  5. Wipe geo entirely if no signal (do NOT keep random junk)

Run in background. Atomic write: write to .tmp, then rename.
"""
import csv
import io
import json
import os
import re
import sys
import time
from urllib.parse import urlparse

# Force UTF-8 stdout for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

CSV_PATH = r"C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv"
TV_CATALOG = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_catalog_full.json"
PROGRESS_PATH = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\geo_rebuild_progress.json"

# ccTLD → country mapping (ISO 3166-1 alpha-2 + display name)
CC_TLD = {
    'ad': ('AD', 'Andorra'), 'ae': ('AE', 'United Arab Emirates'), 'af': ('AF', 'Afghanistan'),
    'al': ('AL', 'Albania'), 'am': ('AM', 'Armenia'), 'ao': ('AO', 'Angola'),
    'ar': ('AR', 'Argentina'), 'as': ('AS', 'American Samoa'), 'at': ('AT', 'Austria'),
    'au': ('AU', 'Australia'), 'aw': ('AW', 'Aruba'), 'ax': ('AX', 'Aland Islands'),
    'az': ('AZ', 'Azerbaijan'), 'ba': ('BA', 'Bosnia and Herzegovina'),
    'bb': ('BB', 'Barbados'), 'bd': ('BD', 'Bangladesh'), 'be': ('BE', 'Belgium'),
    'bf': ('BF', 'Burkina Faso'), 'bg': ('BG', 'Bulgaria'), 'bh': ('BH', 'Bahrain'),
    'bi': ('BI', 'Burundi'), 'bj': ('BJ', 'Benin'), 'bl': ('BL', 'Saint Barthelemy'),
    'bm': ('BM', 'Bermuda'), 'bn': ('BN', 'Brunei Darussalam'),
    'bo': ('BO', 'Bolivia'), 'bq': ('BQ', 'Bonaire'), 'br': ('BR', 'Brazil'),
    'bs': ('BS', 'Bahamas'), 'bt': ('BT', 'Bhutan'), 'bv': ('BV', 'Bouvet Island'),
    'bw': ('BW', 'Botswana'), 'by': ('BY', 'Belarus'), 'bz': ('BZ', 'Belize'),
    'ca': ('CA', 'Canada'), 'cc': ('CC', 'Cocos Islands'), 'cd': ('CD', 'Democratic Republic of the Congo'),
    'cf': ('CF', 'Central African Republic'), 'cg': ('CG', 'Congo'),
    'ch': ('CH', 'Switzerland'), 'ci': ('CI', "Cote d'Ivoire"), 'ck': ('CK', 'Cook Islands'),
    'cl': ('CL', 'Chile'), 'cm': ('CM', 'Cameroon'), 'cn': ('CN', 'China'),
    'co': ('CO', 'Colombia'), 'cr': ('CR', 'Costa Rica'), 'cu': ('CU', 'Cuba'),
    'cv': ('CV', 'Cape Verde'), 'cw': ('CW', 'Curacao'), 'cx': ('CX', 'Christmas Island'),
    'cy': ('CY', 'Cyprus'), 'cz': ('CZ', 'Czech Republic'), 'de': ('DE', 'Germany'),
    'dj': ('DJ', 'Djibouti'), 'dk': ('DK', 'Denmark'), 'dm': ('DM', 'Dominica'),
    'do': ('DO', 'Dominican Republic'), 'dz': ('DZ', 'Algeria'), 'ec': ('EC', 'Ecuador'),
    'ee': ('EE', 'Estonia'), 'eg': ('EG', 'Egypt'), 'eh': ('EH', 'Western Sahara'),
    'er': ('ER', 'Eritrea'), 'es': ('ES', 'Spain'), 'et': ('ET', 'Ethiopia'),
    'eu': ('EU', 'European Union'), 'fi': ('FI', 'Finland'), 'fj': ('FJ', 'Fiji'),
    'fk': ('FK', 'Falkland Islands'), 'fm': ('FM', 'Micronesia'), 'fo': ('FO', 'Faroe Islands'),
    'fr': ('FR', 'France'), 'ga': ('GA', 'Gabon'), 'gb': ('GB', 'United Kingdom'),
    'gd': ('GD', 'Grenada'), 'ge': ('GE', 'Georgia'), 'gf': ('GF', 'French Guiana'),
    'gg': ('GG', 'Guernsey'), 'gh': ('GH', 'Ghana'), 'gi': ('GI', 'Gibraltar'),
    'gl': ('GL', 'Greenland'), 'gm': ('GM', 'Gambia'), 'gn': ('GN', 'Guinea'),
    'gp': ('GP', 'Guadeloupe'), 'gq': ('GQ', 'Equatorial Guinea'), 'gr': ('GR', 'Greece'),
    'gs': ('GS', 'South Georgia'), 'gt': ('GT', 'Guatemala'), 'gu': ('GU', 'Guam'),
    'gw': ('GW', 'Guinea-Bissau'), 'gy': ('GY', 'Guyana'), 'hk': ('HK', 'Hong Kong'),
    'hm': ('HM', 'Heard Island'), 'hn': ('HN', 'Honduras'), 'hr': ('HR', 'Croatia'),
    'ht': ('HT', 'Haiti'), 'hu': ('HU', 'Hungary'), 'id': ('ID', 'Indonesia'),
    'ie': ('IE', 'Ireland'), 'il': ('IL', 'Israel'), 'im': ('IM', 'Isle of Man'),
    'in': ('IN', 'India'), 'io': ('IO', 'British Indian Ocean Territory'),
    'iq': ('IQ', 'Iraq'), 'ir': ('IR', 'Iran'), 'is': ('IS', 'Iceland'),
    'it': ('IT', 'Italy'), 'je': ('JE', 'Jersey'), 'jm': ('JM', 'Jamaica'),
    'jo': ('JO', 'Jordan'), 'jp': ('JP', 'Japan'), 'ke': ('KE', 'Kenya'),
    'kg': ('KG', 'Kyrgyzstan'), 'kh': ('KH', 'Cambodia'), 'ki': ('KI', 'Kiribati'),
    'km': ('KM', 'Comoros'), 'kn': ('KN', 'Saint Kitts and Nevis'),
    'kp': ('KP', 'North Korea'), 'kr': ('KR', 'South Korea'), 'kw': ('KW', 'Kuwait'),
    'ky': ('KY', 'Cayman Islands'), 'kz': ('KZ', 'Kazakhstan'), 'la': ('LA', 'Laos'),
    'lb': ('LB', 'Lebanon'), 'lc': ('LC', 'Saint Lucia'), 'li': ('LI', 'Liechtenstein'),
    'lk': ('LK', 'Sri Lanka'), 'lr': ('LR', 'Liberia'), 'ls': ('LS', 'Lesotho'),
    'lt': ('LT', 'Lithuania'), 'lu': ('LU', 'Luxembourg'), 'lv': ('LV', 'Latvia'),
    'ly': ('LY', 'Libya'), 'ma': ('MA', 'Morocco'), 'mc': ('MC', 'Monaco'),
    'md': ('MD', 'Moldova'), 'me': ('ME', 'Montenegro'), 'mf': ('MF', 'Saint Martin'),
    'mg': ('MG', 'Madagascar'), 'mh': ('MH', 'Marshall Islands'), 'mk': ('MK', 'North Macedonia'),
    'ml': ('ML', 'Mali'), 'mm': ('MM', 'Myanmar'), 'mn': ('MN', 'Mongolia'),
    'mo': ('MO', 'Macao'), 'mp': ('MP', 'Northern Mariana Islands'),
    'mq': ('MQ', 'Martinique'), 'mr': ('MR', 'Mauritania'), 'ms': ('MS', 'Montserrat'),
    'mt': ('MT', 'Malta'), 'mu': ('MU', 'Mauritius'), 'mv': ('MV', 'Maldives'),
    'mw': ('MW', 'Malawi'), 'mx': ('MX', 'Mexico'), 'my': ('MY', 'Malaysia'),
    'mz': ('MZ', 'Mozambique'), 'na': ('NA', 'Namibia'), 'nc': ('NC', 'New Caledonia'),
    'ne': ('NE', 'Niger'), 'nf': ('NF', 'Norfolk Island'), 'ng': ('NG', 'Nigeria'),
    'ni': ('NI', 'Nicaragua'), 'nl': ('NL', 'Netherlands'), 'no': ('NO', 'Norway'),
    'np': ('NP', 'Nepal'), 'nr': ('NR', 'Nauru'), 'nu': ('NU', 'Niue'),
    'nz': ('NZ', 'New Zealand'), 'om': ('OM', 'Oman'), 'pa': ('PA', 'Panama'),
    'pe': ('PE', 'Peru'), 'pf': ('PF', 'French Polynesia'),
    'pg': ('PG', 'Papua New Guinea'), 'ph': ('PH', 'Philippines'),
    'pk': ('PK', 'Pakistan'), 'pl': ('PL', 'Poland'), 'pm': ('PM', 'Saint Pierre and Miquelon'),
    'pn': ('PN', 'Pitcairn'), 'pr': ('PR', 'Puerto Rico'), 'ps': ('PS', 'Palestine'),
    'pt': ('PT', 'Portugal'), 'pw': ('PW', 'Palau'), 'py': ('PY', 'Paraguay'),
    'qa': ('QA', 'Qatar'), 're': ('RE', 'Reunion'), 'ro': ('RO', 'Romania'),
    'rs': ('RS', 'Serbia'), 'ru': ('RU', 'Russia'), 'rw': ('RW', 'Rwanda'),
    'sa': ('SA', 'Saudi Arabia'), 'sb': ('SB', 'Solomon Islands'), 'sc': ('SC', 'Seychelles'),
    'sd': ('SD', 'Sudan'), 'se': ('SE', 'Sweden'), 'sg': ('SG', 'Singapore'),
    'sh': ('SH', 'Saint Helena'), 'si': ('SI', 'Slovenia'),
    'sj': ('SJ', 'Svalbard and Jan Mayen'), 'sk': ('SK', 'Slovakia'),
    'sl': ('SL', 'Sierra Leone'), 'sm': ('SM', 'San Marino'), 'sn': ('SN', 'Senegal'),
    'so': ('SO', 'Somalia'), 'sr': ('SR', 'Suriname'), 'ss': ('SS', 'South Sudan'),
    'st': ('ST', 'Sao Tome and Principe'), 'sv': ('SV', 'El Salvador'),
    'sx': ('SX', 'Sint Maarten'), 'sy': ('SY', 'Syria'), 'sz': ('SZ', 'Eswatini'),
    'tc': ('TC', 'Turks and Caicos Islands'), 'td': ('TD', 'Chad'),
    'tf': ('TF', 'French Southern Territories'), 'tg': ('TG', 'Togo'),
    'th': ('TH', 'Thailand'), 'tj': ('TJ', 'Tajikistan'), 'tk': ('TK', 'Tokelau'),
    'tl': ('TL', 'Timor-Leste'), 'tm': ('TM', 'Turkmenistan'), 'tn': ('TN', 'Tunisia'),
    'to': ('TO', 'Tonga'), 'tp': ('TP', 'East Timor'), 'tr': ('TR', 'Turkey'),
    'tt': ('TT', 'Trinidad and Tobago'), 'tv': ('TV', 'Tuvalu'),
    'tw': ('TW', 'Taiwan'), 'tz': ('TZ', 'Tanzania'), 'ua': ('UA', 'Ukraine'),
    'ug': ('UG', 'Uganda'), 'uk': ('GB', 'United Kingdom'), 'um': ('UM', 'US Minor Outlying Islands'),
    'us': ('US', 'United States'), 'uy': ('UY', 'Uruguay'), 'uz': ('UZ', 'Uzbekistan'),
    'va': ('VA', 'Vatican City'), 'vc': ('VC', 'Saint Vincent and the Grenadines'),
    've': ('VE', 'Venezuela'), 'vg': ('VG', 'British Virgin Islands'),
    'vi': ('VI', 'US Virgin Islands'), 'vn': ('VN', 'Vietnam'), 'vu': ('VU', 'Vanuatu'),
    'wf': ('WF', 'Wallis and Futuna'), 'ws': ('WS', 'Samoa'), 'xk': ('XK', 'Kosovo'),
    'ye': ('YE', 'Yemen'), 'yt': ('YT', 'Mayotte'), 'za': ('ZA', 'South Africa'),
    'zm': ('ZM', 'Zambia'), 'zw': ('ZW', 'Zimbabwe'),
    # generic TLDs
    'com': None, 'org': None, 'net': None, 'edu': None, 'gov': None, 'int': None, 'mil': None,
    'biz': None, 'info': None, 'name': None, 'pro': None, 'museum': None,
    'aero': None, 'coop': None, 'mobi': None, 'tel': None, 'cat': None, 'asia': None,
}

# US state DOT / agency host → (state name, country, default lat, default lon)
US_STATE_HOSTS = {
    # State DOTs
    'iowadot.gov': ('Iowa', 'United States', 41.878, -93.097),
    'dot.ca.gov': ('California', 'United States', 36.778, -119.417),
    'caltrans': ('California', 'United States', 36.778, -119.417),
    'txdot.gov': ('Texas', 'United States', 31.968, -99.901),
    'fl511.com': ('Florida', 'United States', 27.664, -81.515),
    '511ga': ('Georgia', 'United States', 32.165, -82.900),
    '511ny': ('New York', 'United States', 42.712, -74.006),
    '511mn': ('Minnesota', 'United States', 46.729, -94.685),
    '511pa': ('Pennsylvania', 'United States', 40.590, -77.209),
    'wsdot': ('Washington', 'United States', 47.751, -120.740),
    'udot': ('Utah', 'United States', 39.419, -111.950),
    'vdot': ('Virginia', 'United States', 37.769, -78.170),
    'mdot': ('Maryland', 'United States', 39.063, -76.802),
    'cdot': ('Colorado', 'United States', 39.059, -105.311),
    'idot': ('Illinois', 'United States', 40.349, -88.986),
    'illinois': ('Illinois', 'United States', 40.349, -88.986),
    'ordot': ('Oregon', 'United States', 44.572, -122.070),
    'ndot': ('Nebraska', 'United States', 41.492, -99.901),
    'odot': ('Ohio', 'United States', 40.388, -82.764),
    'wisdot': ('Wisconsin', 'United States', 44.268, -89.616),
    'michigan.gov': ('Michigan', 'United States', 43.326, -84.536),
    'indot': ('Indiana', 'United States', 40.267, -86.134),
    'kydot': ('Kentucky', 'United States', 37.668, -84.670),
    'tndot': ('Tennessee', 'United States', 35.747, -86.692),
    'alabamatraffic': ('Alabama', 'United States', 32.806, -86.791),
    'mdotmaryland': ('Maryland', 'United States', 39.063, -76.802),
    'itd.idaho.gov': ('Idaho', 'United States', 44.068, -114.742),
    'mt.gov': ('Montana', 'United States', 46.879, -110.362),
    'wyo.gov': ('Wyoming', 'United States', 42.756, -107.208),
    'akdot': ('Alaska', 'United States', 64.200, -149.493),
    'hawaii.gov': ('Hawaii', 'United States', 19.896, -155.582),
    'ncdot': ('North Carolina', 'United States', 35.630, -79.806),
    'drivenc': ('North Carolina', 'United States', 35.630, -79.806),
    'scdot': ('South Carolina', 'United States', 33.836, -81.163),
    'scdot': ('South Carolina', 'United States', 33.836, -81.163),
    'gdot': ('Georgia', 'United States', 32.165, -82.900),
    'fdot': ('Florida', 'United States', 27.664, -81.515),
    'ladot': ('Louisiana', 'United States', 31.169, -91.867),
    'modot': ('Missouri', 'United States', 37.964, -91.831),
    'ardot': ('Arkansas', 'United States', 34.969, -92.373),
    'nmdot': ('New Mexico', 'United States', 34.840, -106.248),
    'azdot': ('Arizona', 'United States', 34.049, -111.093),
    'nvroads': ('Nevada', 'United States', 38.802, -116.419),
    'ksdot': ('Kansas', 'United States', 38.526, -96.726),
    'sd511': ('South Dakota', 'United States', 44.299, -99.438),
    'ndroads': ('North Dakota', 'United States', 47.551, -100.302),
    'ctroads': ('Connecticut', 'United States', 41.603, -73.087),
    'nhdhr': ('New Hampshire', 'United States', 43.452, -71.563),
    'vermont': ('Vermont', 'United States', 44.045, -72.710),
    'maine.gov': ('Maine', 'United States', 44.693, -69.381),
    'mass511': ('Massachusetts', 'United States', 42.407, -71.382),
    'ri511': ('Rhode Island', 'United States', 41.580, -71.477),
    'newjersey': ('New Jersey', 'United States', 40.298, -74.521),
    'nj511': ('New Jersey', 'United States', 40.298, -74.521),
    'de511': ('Delaware', 'United States', 39.318, -75.507),
    # Cameras
    'alertcalifornia': ('California', 'United States', 36.778, -119.417),
    'earthcam': ('United States', 'United States', 39.828, -98.579),
    'skylinewebcams': ('Italy', 'Italy', 41.872, 12.567),  # HQ in Italy
    'earthcam.com': ('United States', 'United States', 39.828, -98.579),
    'abbeyroad.com': ('United Kingdom', 'United Kingdom', 51.532, -0.179),  # Abbey Road London
    'youwebcams': ('Italy', 'Italy', 41.872, 12.567),
    'webcamtaxi': ('Italy', 'Italy', 41.872, 12.567),
    'webcamera24': ('Germany', 'Germany', 51.165, 10.451),
    # Italian
    'autostrade.it': ('Italy', 'Italy', 41.872, 12.567),
    'video.autostrade.it': ('Italy', 'Italy', 41.872, 12.567),
    # Country-level
    '511': ('United States', 'United States', 39.828, -98.579),
    'tfl': ('United Kingdom', 'United Kingdom', 51.507, -0.127),  # Transport for London
    'opentopomap': ('Global', None, None, None),
    'argus': ('Global', None, None, None),
}

# Country name → ISO code lookup
_tv_pairs = []
for _v in CC_TLD.values():
    if _v and isinstance(_v, tuple) and len(_v) == 2:
        _tv_pairs.append(_v)
COUNTRY_TO_CODE = {n: c for c, n in _tv_pairs}
COUNTRY_CODE_TO_NAME = {c: n for c, n in _tv_pairs}
# Add aliases
ALIASES = {
    'United States of America': 'United States',
    'USA': 'United States',
    'US': 'United States',
    'UK': 'United Kingdom',
    'Britain': 'United Kingdom',
    'Great Britain': 'United Kingdom',
    'England': 'United Kingdom',
    'Russia': 'Russia',
    'Russian Federation': 'Russia',
    'China': 'China',
    "People's Republic of China": 'China',
    'PRC': 'China',
    'Korea': 'South Korea',
    'South Korea': 'South Korea',
    'Republic of Korea': 'South Korea',
    'North Korea': 'North Korea',
    "Democratic People's Republic of Korea": 'North Korea',
    'Taiwan': 'Taiwan',
    'Republic of China': 'Taiwan',
    'Italia': 'Italy',
    'Brasil': 'Brazil',
    'España': 'Spain',
    'Deutschland': 'Germany',
    '日本': 'Japan',
    '中国': 'China',
    '臺灣': 'Taiwan',
    '台湾': 'Taiwan',
    'Россия': 'Russia',
    'Беларусь': 'Belarus',
    'Україна': 'Ukraine',
    'ไทย': 'Thailand',
    'ประเทศไทย': 'Thailand',
}
for k, v in ALIASES.items():
    COUNTRY_TO_CODE[k] = COUNTRY_TO_CODE.get(v, 'XX')


def get_tld_country(host):
    """Extract ccTLD → (code, name) or None if generic."""
    if not host:
        return None
    host = host.lower()
    # last dot
    parts = host.split('.')
    if len(parts) < 2:
        return None
    tld = parts[-1]
    if tld in CC_TLD and CC_TLD[tld]:
        return CC_TLD[tld]
    # 2-part TLD like .co.uk, .com.au
    if len(parts) >= 3:
        tld2 = parts[-2] + '.' + parts[-1]
        if tld2 in ('co.uk', 'org.uk', 'ac.uk', 'gov.uk'):
            return ('GB', 'United Kingdom')
        if tld2 in ('com.au', 'net.au', 'org.au', 'edu.au', 'gov.au'):
            return ('AU', 'Australia')
        if tld2 in ('co.jp'):
            return ('JP', 'Japan')
        if tld2 in ('co.kr'):
            return ('KR', 'South Korea')
        if tld2 in ('co.in', 'net.in', 'org.in'):
            return ('IN', 'India')
        if tld2 in ('co.nz', 'net.nz', 'org.nz'):
            return ('NZ', 'New Zealand')
        if tld2 in ('co.za'):
            return ('ZA', 'South Africa')
        if tld2 in ('com.br', 'net.br', 'org.br'):
            return ('BR', 'Brazil')
    return None


def get_host_geo(host):
    """Look up host in US_STATE_HOSTS. Returns (region, country, lat, lon) or None."""
    if not host:
        return None
    host = host.lower()
    # Try direct match
    for key, geo in US_STATE_HOSTS.items():
        if key in host:
            return geo
    return None


def normalize_country(name):
    """Normalize country name to canonical form."""
    if not name:
        return None
    name = name.strip()
    if name in COUNTRY_TO_CODE:
        return name
    if name in ALIASES:
        return ALIASES[name]
    return name  # return as-is


def main():
    # Load TV catalog
    print("Loading TrafficVision catalog...", flush=True)
    t0 = time.time()
    with open(TV_CATALOG, 'r', encoding='utf-8') as f:
        tv = json.load(f)
    tv_cams = tv.get('cameras', [])
    print(f"  Loaded {len(tv_cams)} TV cams in {time.time()-t0:.1f}s", flush=True)

    # Build TV lookup by (source, host) → cam
    print("Building TV lookup indexes...", flush=True)
    t0 = time.time()
    tv_by_source = {}  # source → [cam, cam, ...]
    tv_by_host = {}    # host → [cam, cam, ...]
    for c in tv_cams:
        s = c.get('source', '')
        if s:
            tv_by_source.setdefault(s, []).append(c)
        url = c.get('sourceUrl', '') or c.get('url', '') or ''
        if url:
            try:
                h = urlparse(url).hostname or ''
                h = h.lower()
                if h:
                    tv_by_host.setdefault(h, []).append(c)
            except:
                pass
    print(f"  Built indexes ({len(tv_by_source)} sources, {len(tv_by_host)} hosts) in {time.time()-t0:.1f}s", flush=True)

    # Counters
    stats = {
        'total': 0,
        'tv_matched': 0,
        'tld_matched': 0,
        'host_matched': 0,
        'unchanged': 0,
        'overwritten': 0,
        'wiped': 0,
        'no_signal': 0,
    }

    # Read CSV
    print("Reading CSV...", flush=True)
    t0 = time.time()
    with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = [row for row in reader]
    print(f"  Read {len(rows)} rows in {time.time()-t0:.1f}s", flush=True)

    # Column indices
    IDX = {col: i for i, col in enumerate(header)}
    # idx=0, project_name=1, url=2, live_stream_url=3, type=4, auth=5,6,7, enabled=8,
    # live_status=9, http_status=10, content_type=11, server_header=12, page_title=13,
    # description=14, category=15, likely_subject=16, brand=17, model=18,
    # country=19, region=20, city=21, zip=22, address=23, lat=24, lon=25, geo_source=26,
    # isp=27, org=28, asn=29, reverse_dns=30?, host=31?, confidence=32, notes=33, csv_id=34
    # Per prior notes: host=32, but the actual layout from argus rows shows host is at index 32
    # Let me verify the actual layout
    if len(header) != 35:
        print(f"WARNING: Expected 35 columns, got {len(header)}", flush=True)
        print(f"Header: {header}", flush=True)
    COL_IDX = IDX['idx']
    COL_URL = IDX['url']
    COL_LIVE = IDX.get('live_stream_url', 3)
    COL_COUNTRY = IDX['country']
    COL_REGION = IDX['region']
    COL_CITY = IDX['city']
    COL_LAT = IDX['lat']
    COL_LON = IDX['lon']
    COL_GEO_SRC = IDX['geo_source']
    COL_HOST = IDX.get('host', 32)
    COL_NOTES = IDX.get('notes', 33)

    # Build per-host TV lookup with argus_id if available
    print("Building argus_id -> TV id map...", flush=True)
    t0 = time.time()
    argus_id_to_tv = {}  # e.g. "alertca-880" → tv_cam
    for src, cams in tv_by_source.items():
        for c in cams:
            tid = c.get('id', '')
            if not tid:
                continue
            # TV id like "alertcalifornia-Axis-AlabamaHills1"
            # argus_id like "opencctv_alertcalifornia_alertca-880"
            # The "880" is internal argus index, not in TV id
            # So argus_id→TV id mapping is hard. Skip argus_id matching, use host instead.
            pass
    print(f"  Done in {time.time()-t0:.1f}s", flush=True)

    # Process each row
    print("Processing rows...", flush=True)
    t0 = time.time()
    report = []
    for i, row in enumerate(rows):
        if i % 10000 == 0 and i > 0:
            elapsed = time.time() - t0
            rate = i / elapsed
            print(f"  {i}/{len(rows)} ({rate:.0f}/s) — {stats}", flush=True)
            with open(PROGRESS_PATH, 'w') as pf:
                json.dump({'stats': stats, 'last_idx': i}, pf)

        stats['total'] += 1
        url = row[COL_URL] if COL_URL < len(row) else ''
        host = row[COL_HOST] if COL_HOST < len(row) else ''
        live = row[COL_LIVE] if COL_LIVE < len(row) else ''
        notes = row[COL_NOTES] if COL_NOTES < len(row) else ''
        old_country = row[COL_COUNTRY] if COL_COUNTRY < len(row) else ''
        old_lat = row[COL_LAT] if COL_LAT < len(row) else ''
        old_lon = row[COL_LON] if COL_LON < len(row) else ''

        # Pick best host signal
        best_host = host or live
        if not best_host and url:
            best_host = url
        if not best_host:
            stats['no_signal'] += 1
            continue

        try:
            parsed = urlparse(best_host)
            hostname = (parsed.hostname or '').lower()
        except:
            hostname = ''

        new_country = None
        new_region = None
        new_city = None
        new_lat = None
        new_lon = None
        source_used = None

        # 1. TV match by host
        if hostname and hostname in tv_by_host:
            tv_cams_for_host = tv_by_host[hostname]
            # Pick first
            tvc = tv_cams_for_host[0]
            new_country = normalize_country(tvc.get('country', ''))
            new_region = tvc.get('state', '') or tvc.get('county', '') or ''
            new_city = tvc.get('city', '') or tvc.get('location', '') or ''
            new_lat = tvc.get('lat')
            new_lon = tvc.get('lng')
            source_used = f'tv_host:{hostname}'
            stats['tv_matched'] += 1

        # 2. TLD inference
        if not new_country:
            tld = get_tld_country(hostname)
            if tld:
                new_country = tld[1]
                new_lat = None
                new_lon = None
                new_city = None
                new_region = None
                source_used = f'tld:{hostname.split(".")[-1]}'
                stats['tld_matched'] += 1

        # 3. Host → state DOT lookup
        if not new_country and hostname:
            hg = get_host_geo(hostname)
            if hg:
                region, country, lat, lon = hg
                if country:
                    new_country = country
                    new_region = region if region != 'Global' else None
                    if lat is not None:
                        new_lat = lat
                        new_lon = lon
                    source_used = f'host:{hostname}'
                    stats['host_matched'] += 1

        # Apply or wipe
        if new_country is not None:
            # Update row
            changed = (old_country != new_country or
                       (old_lat and new_lat and str(old_lat) != str(new_lat)) or
                       (old_lon and new_lon and str(old_lon) != str(new_lon)))
            row[COL_COUNTRY] = new_country
            if new_region is not None:
                row[COL_REGION] = new_region
            if new_city is not None:
                row[COL_CITY] = new_city
            if new_lat is not None:
                row[COL_LAT] = str(new_lat)
            if new_lon is not None:
                row[COL_LON] = str(new_lon)
            row[COL_GEO_SRC] = source_used or 'rebuild'
            if changed:
                stats['overwritten'] += 1
            else:
                stats['unchanged'] += 1
        else:
            # No signal — wipe bogus geo
            if old_country or old_lat or old_lon:
                row[COL_COUNTRY] = ''
                row[COL_REGION] = ''
                row[COL_CITY] = ''
                row[COL_LAT] = ''
                row[COL_LON] = ''
                row[COL_GEO_SRC] = 'wiped'
                stats['wiped'] += 1
            else:
                stats['no_signal'] += 1

    print(f"Processed {len(rows)} in {time.time()-t0:.1f}s", flush=True)
    print(f"Final stats: {stats}", flush=True)

    # Write to .tmp then rename
    print("Writing atomic CSV...", flush=True)
    tmp = CSV_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        w.writerow(header)
        for row in rows:
            w.writerow(row)
    os.replace(tmp, CSV_PATH)
    print(f"Done. Saved to {CSV_PATH}", flush=True)
    with open(PROGRESS_PATH, 'w') as pf:
        json.dump({'stats': stats, 'done': True}, pf)


if __name__ == '__main__':
    main()
