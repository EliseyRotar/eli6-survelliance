"""
geo_rebuild_v2.py - Smart geo rebuild using:
  1. TV source matching (extract source from notes/argus_id, get country from TV)
  2. Host -> state/country lookup (top 200 agency hosts)
  3. TLD inference (.it, .jp, .de, etc.)
  4. NO WIPING - if no signal, keep existing geo

Safer than v1 (no destructive writes).
"""
import csv
import io
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from urllib.parse import urlparse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

CSV_PATH = r"C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv"
TV_CATALOG = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_catalog_full.json"
PROGRESS_PATH = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\geo_rebuild_v2_progress.json"

# ============ ccTLD -> (code, name) ============
CC_TLD = {
    'ad': ('AD', 'Andorra'), 'ae': ('AE', 'United Arab Emirates'), 'af': ('AF', 'Afghanistan'),
    'al': ('AL', 'Albania'), 'am': ('AM', 'Armenia'), 'ao': ('AO', 'Angola'),
    'ar': ('AR', 'Argentina'), 'as': ('AS', 'American Samoa'), 'at': ('AT', 'Austria'),
    'au': ('AU', 'Australia'), 'aw': ('AW', 'Aruba'), 'az': ('AZ', 'Azerbaijan'),
    'ba': ('BA', 'Bosnia and Herzegovina'), 'bb': ('BB', 'Barbados'),
    'bd': ('BD', 'Bangladesh'), 'be': ('BE', 'Belgium'), 'bf': ('BF', 'Burkina Faso'),
    'bg': ('BG', 'Bulgaria'), 'bh': ('BH', 'Bahrain'), 'bi': ('BI', 'Burundi'),
    'bj': ('BJ', 'Benin'), 'bm': ('BM', 'Bermuda'), 'bn': ('BN', 'Brunei Darussalam'),
    'bo': ('BO', 'Bolivia'), 'br': ('BR', 'Brazil'), 'bs': ('BS', 'Bahamas'),
    'bt': ('BT', 'Bhutan'), 'bw': ('BW', 'Botswana'), 'by': ('BY', 'Belarus'),
    'bz': ('BZ', 'Belize'), 'ca': ('CA', 'Canada'), 'cd': ('CD', 'Democratic Republic of the Congo'),
    'cf': ('CF', 'Central African Republic'), 'cg': ('CG', 'Congo'),
    'ch': ('CH', 'Switzerland'), 'ci': ('CI', "Cote d'Ivoire"), 'ck': ('CK', 'Cook Islands'),
    'cl': ('CL', 'Chile'), 'cm': ('CM', 'Cameroon'), 'cn': ('CN', 'China'),
    'co': ('CO', 'Colombia'), 'cr': ('CR', 'Costa Rica'), 'cu': ('CU', 'Cuba'),
    'cv': ('CV', 'Cape Verde'), 'cw': ('CW', 'Curacao'), 'cy': ('CY', 'Cyprus'),
    'cz': ('CZ', 'Czech Republic'), 'de': ('DE', 'Germany'), 'dj': ('DJ', 'Djibouti'),
    'dk': ('DK', 'Denmark'), 'dm': ('DM', 'Dominica'), 'do': ('DO', 'Dominican Republic'),
    'dz': ('DZ', 'Algeria'), 'ec': ('EC', 'Ecuador'), 'ee': ('EE', 'Estonia'),
    'eg': ('EG', 'Egypt'), 'er': ('ER', 'Eritrea'), 'es': ('ES', 'Spain'),
    'et': ('ET', 'Ethiopia'), 'fi': ('FI', 'Finland'), 'fj': ('FJ', 'Fiji'),
    'fk': ('FK', 'Falkland Islands'), 'fm': ('FM', 'Micronesia'), 'fo': ('FO', 'Faroe Islands'),
    'fr': ('FR', 'France'), 'ga': ('GA', 'Gabon'), 'gb': ('GB', 'United Kingdom'),
    'gd': ('GD', 'Grenada'), 'ge': ('GE', 'Georgia'), 'gf': ('GF', 'French Guiana'),
    'gg': ('GG', 'Guernsey'), 'gh': ('GH', 'Ghana'), 'gi': ('GI', 'Gibraltar'),
    'gl': ('GL', 'Greenland'), 'gm': ('GM', 'Gambia'), 'gn': ('GN', 'Guinea'),
    'gp': ('GP', 'Guadeloupe'), 'gq': ('GQ', 'Equatorial Guinea'), 'gr': ('GR', 'Greece'),
    'gs': ('GS', 'South Georgia'), 'gt': ('GT', 'Guatemala'), 'gu': ('GU', 'Guam'),
    'gw': ('GW', 'Guinea-Bissau'), 'gy': ('GY', 'Guyana'), 'hk': ('HK', 'Hong Kong'),
    'hn': ('HN', 'Honduras'), 'hr': ('HR', 'Croatia'), 'ht': ('HT', 'Haiti'),
    'hu': ('HU', 'Hungary'), 'id': ('ID', 'Indonesia'), 'ie': ('IE', 'Ireland'),
    'il': ('IL', 'Israel'), 'im': ('IM', 'Isle of Man'), 'in': ('IN', 'India'),
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
    'md': ('MD', 'Moldova'), 'me': ('ME', 'Montenegro'), 'mg': ('MG', 'Madagascar'),
    'mh': ('MH', 'Marshall Islands'), 'mk': ('MK', 'North Macedonia'),
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
    'to': ('TO', 'Tonga'), 'tr': ('TR', 'Turkey'), 'tt': ('TT', 'Trinidad and Tobago'),
    'tv': ('TV', 'Tuvalu'), 'tw': ('TW', 'Taiwan'), 'tz': ('TZ', 'Tanzania'),
    'ua': ('UA', 'Ukraine'), 'ug': ('UG', 'Uganda'), 'uk': ('GB', 'United Kingdom'),
    'us': ('US', 'United States'), 'uy': ('UY', 'Uruguay'), 'uz': ('UZ', 'Uzbekistan'),
    'va': ('VA', 'Vatican City'), 'vc': ('VC', 'Saint Vincent and the Grenadines'),
    've': ('VE', 'Venezuela'), 'vg': ('VG', 'British Virgin Islands'),
    'vi': ('VI', 'US Virgin Islands'), 'vn': ('VN', 'Vietnam'), 'vu': ('VU', 'Vanuatu'),
    'wf': ('WF', 'Wallis and Futuna'), 'ws': ('WS', 'Samoa'), 'xk': ('XK', 'Kosovo'),
    'ye': ('YE', 'Yemen'), 'yt': ('YT', 'Mayotte'), 'za': ('ZA', 'South Africa'),
    'zm': ('ZM', 'Zambia'), 'zw': ('ZW', 'Zimbabwe'),
}

# ============ Comprehensive host -> (state/region, country) lookup ============
# Built from top CSV hosts + agency knowledge
HOST_GEO = {
    # ===== US State DOTs and traffic agencies =====
    'wzmedia.dot.ca.gov': ('California', 'United States'),
    'udottraffic.utah.gov': ('Utah', 'United States'),
    'images.wsdot.wa.gov': ('Washington', 'United States'),
    'cctv.travelmidwest.com': ('Illinois', 'United States'),  # multi-state but IL
    'cwwp2.dot.ca.gov': ('California', 'United States'),
    'prod-ut.ibi511.com': ('Utah', 'United States'),
    'cameras.alertcalifornia.org': ('California', 'United States'),
    'www.511pa.com': ('Pennsylvania', 'United States'),
    'video.dot.state.mn.us': ('Minnesota', 'United States'),
    'tripcheck.com': ('Oregon', 'United States'),
    'www.houstontranstar.org': ('Texas', 'United States'),
    'drivebc.ca': ('British Columbia', 'Canada'),
    'webcams.nyctmc.org': ('New York', 'United States'),
    '511on.ca': ('Ontario', 'Canada'),
    'www.nvroads.com': ('Nevada', 'United States'),
    'tpktraffic.com': ('Florida', 'United States'),  # Tampa PK
    'publicstreamer1.cotrip.org': ('Colorado', 'United States'),
    'cctv.austinmobility.io': ('Texas', 'United States'),
    'kamera.atlas.vegvesen.no': ('Norway', 'Norway'),
    'public.carsprogram.org': ('United States', 'United States'),  # generic US
    'skysfs3.trafficwise.org': ('Iowa', 'United States'),
    'www.wyoroad.info': ('Wyoming', 'United States'),
    'traffic.ottawa.ca': ('Ontario', 'Canada'),
    'api.algotraffic.com': ('Alberta', 'Canada'),
    'micamerasimages.net': ('Michigan', 'United States'),
    'www.511nj.org': ('New Jersey', 'United States'),
    'www.fl511.com': ('Florida', 'United States'),
    'images.511ga.org': ('Georgia', 'United States'),
    '511ga.org': ('Georgia', 'United States'),
    'nyctmc.org': ('New York', 'United States'),
    'wx.ahtd.arkansas.gov': ('Arkansas', 'United States'),
    'images.aroad.com': ('Alabama', 'United States'),
    'www.tdotabc.com': ('Tennessee', 'United States'),
    'www.drivemyelvis.com': ('Mississippi', 'United States'),
    'www.drivemaui.com': ('Hawaii', 'United States'),
    'www.drivetexas.org': ('Texas', 'United States'),
    'www.ksdot.org': ('Kansas', 'United States'),
    'www.ohgo.com': ('Ohio', 'United States'),
    'www.idrivearkansas.com': ('Arkansas', 'United States'),
    'www.carsprogram.org': ('United States', 'United States'),
    'www.iowadot.gov': ('Iowa', 'United States'),
    'iowadot.gov': ('Iowa', 'United States'),
    'atmsqf.iowadot.gov': ('Iowa', 'United States'),
    '511wi.gov': ('Wisconsin', 'United States'),
    'www.511wi.gov': ('Wisconsin', 'United States'),
    'www.smartroute.org': ('United States', 'United States'),
    'www.michigan.gov': ('Michigan', 'United States'),
    'www.gobeachcam.com': ('Florida', 'United States'),
    'www.trafficview.org': ('United States', 'United States'),
    'www.flhsmv.gov': ('Florida', 'United States'),
    'www.kytc.ky.gov': ('Kentucky', 'United States'),
    'transportation.ky.gov': ('Kentucky', 'United States'),
    'www.codot.gov': ('Colorado', 'United States'),
    'www.cotrip.org': ('Colorado', 'United States'),
    'cotrip.org': ('Colorado', 'United States'),
    'www.indot.carsprogram.org': ('Indiana', 'United States'),
    'www.drivenc.gov': ('North Carolina', 'United States'),
    'drivenc.gov': ('North Carolina', 'United States'),
    'www.drivenc.com': ('North Carolina', 'United States'),
    'drivenc.com': ('North Carolina', 'United States'),
    'scdhec.gov': ('South Carolina', 'United States'),
    'www.511sc.org': ('South Carolina', 'United States'),
    'www.scdot.org': ('South Carolina', 'United States'),
    'www.511la.org': ('Louisiana', 'United States'),
    '511la.org': ('Louisiana', 'United States'),
    'www.az511.com': ('Arizona', 'United States'),
    'az511.com': ('Arizona', 'United States'),
    'www.nmroads.com': ('New Mexico', 'United States'),
    'nmroads.com': ('New Mexico', 'United States'),
    'www.nddot.gov': ('North Dakota', 'United States'),
    'www.sddot.com': ('South Dakota', 'United States'),
    'sd511.org': ('South Dakota', 'United States'),
    'www.nebraska511.com': ('Nebraska', 'United States'),
    'www.511nebraska.org': ('Nebraska', 'United States'),
    'www.511mtss.com': ('United States', 'United States'),
    'www.modot.org': ('Missouri', 'United States'),
    'www.idot.illinois.gov': ('Illinois', 'United States'),
    'www.mapquest.com': ('United States', 'United States'),
    'www.deldot.gov': ('Delaware', 'United States'),
    'www.tripcheck.com': ('Oregon', 'United States'),
    'images.itsmarta.org': ('Georgia', 'United States'),
    'www.511virginia.org': ('Virginia', 'United States'),
    'www.511.org': ('United States', 'United States'),
    'newjersey.jpg': ('New Jersey', 'United States'),
    'its.ny.gov': ('New York', 'United States'),
    'www.dot.ny.gov': ('New York', 'United States'),
    'www.511ny.org': ('New York', 'United States'),
    'nyctmc.com': ('New York', 'United States'),
    'cctv.tbkc.gov.tw': ('Taipei', 'Taiwan'),
    'cctv.freeway.gov.tw': ('Taiwan', 'Taiwan'),
    'www.freeway.gov.tw': ('Taiwan', 'Taiwan'),
    'c02.twipcam.com': ('Taiwan', 'Taiwan'),
    'cam.river.go.jp': ('Japan', 'Japan'),
    'road-info-prvs.mlit.go.jp': ('Japan', 'Japan'),
    'jartic.or.jp': ('Japan', 'Japan'),
    'www.mlit.go.jp': ('Japan', 'Japan'),
    'www.jartic.or.jp': ('Japan', 'Japan'),
    'images-webcams.windy.com': ('Global', None),  # Skip
    'imgproxy.windy.com': ('Global', None),  # Skip
    'media.trafficvision.live': ('United States', 'United States'),
    'images.weatherstem.com': ('United States', 'United States'),
    'webcams.opensnow.com': ('United States', 'United States'),
    'data.nottinghamtravelwise.org.uk': ('United Kingdom', 'United Kingdom'),
    'etraffic.dgt.es': ('Spain', 'Spain'),
    'map.bayerninfo.de': ('Germany', 'Germany'),
    'api.trafikinfo.trafikverket.se': ('Sweden', 'Sweden'),
    'video.autostrade.it': ('Italy', 'Italy'),
    'autostrade.it': ('Italy', 'Italy'),
    'weathercam.digitraffic.fi': ('Finland', 'Finland'),
    'digitraffic.fi': ('Finland', 'Finland'),
    'www.avametnuvol.es': ('Spain', 'Spain'),
    'geobilbao.eus': ('Spain', 'Spain'),
    'avo.alaska.edu': ('Alaska', 'United States'),
    'view.myairportcams.com': ('United States', 'United States'),
    'ITSStreamingBR.dotd.la.gov': ('Louisiana', 'United States'),
    'tdcctv.data.one.gov.hk': ('Hong Kong', 'Hong Kong'),
    'phenocam.nau.edu': ('United States', 'United States'),
    'wtvpict.feratel.com': ('Austria', 'Austria'),  # HQ Austria
    'wtvthmb.feratel.com': ('Austria', 'Austria'),
    'feratel.com': ('Austria', 'Austria'),
    'usgs-nims-images.s3.amazonaws.com': ('United States', 'United States'),
    's3-eu-west-1.amazonaws.com': ('Global', None),
    's3.amazonaws.com': ('Global', None),
    'amazonaws.com': ('Global', None),
    'informo.madrid.es': ('Madrid', 'Spain'),
    'quebec511.info': ('Quebec', 'Canada'),
    'lake.county': ('Illinois', 'United States'),
    'lakecountypassage.com': ('Illinois', 'United States'),
    'youtube.com': ('Global', None),
    'youtu.be': ('Global', None),
    'img.youtube.com': ('Global', None),
    'i.ytimg.com': ('Global', None),
    # Asia
    'gts.com.tw': ('Taiwan', 'Taiwan'),
    'eoc.yunlin.gov.tw': ('Taiwan', 'Taiwan'),
    'cctv.tycg.gov.tw': ('Taoyuan', 'Taiwan'),
    'cctv.tc.nantou.gov.tw': ('Taiwan', 'Taiwan'),
    'tbkc.gov.tw': ('Taipei', 'Taiwan'),
    'taipei.gov.tw': ('Taipei', 'Taiwan'),
    'kctmc.kcg.gov.tw': ('Kaohsiung', 'Taiwan'),
    'tmcland.tmc.gov.tw': ('Taiwan', 'Taiwan'),
    'tmc.gov.tw': ('Taiwan', 'Taiwan'),
    'tcc.gov.tw': ('Taichung', 'Taiwan'),
    'thb.gov.tw': ('Taiwan', 'Taiwan'),
    '168.thb.gov.tw': ('Taiwan', 'Taiwan'),
    'taitung.gov.tw': ('Taiwan', 'Taiwan'),
    'miaoli.gov.tw': ('Miaoli', 'Taiwan'),
    'ylhi.gov.tw': ('Taiwan', 'Taiwan'),
    's3.ap-southeast-1.amazonaws.com': ('Singapore', 'Singapore'),
    'tpehb.gov.tw': ('Taipei', 'Taiwan'),
    'taipei.taipei': ('Taipei', 'Taiwan'),
    # Europe
    'www.trafikverket.se': ('Sweden', 'Sweden'),
    'www.trafiken.nu': ('Sweden', 'Sweden'),
    'www.inforoutes06.fr': ('France', 'France'),
    'www.bison-fute.gouv.fr': ('France', 'France'),
    'www.rws.nl': ('Netherlands', 'Netherlands'),
    'www.wegenenverkeer.be': ('Belgium', 'Belgium'),
    'www.verkehrslage.de': ('Germany', 'Germany'),
    'www.autobahn.de': ('Germany', 'Germany'),
    'www.svz.de': ('Germany', 'Germany'),
    'www.strassen-sh.de': ('Germany', 'Germany'),
    'liikennetilanne.fintraffic.fi': ('Finland', 'Finland'),
    'fintraffic.fi': ('Finland', 'Finland'),
    'www.fintraffic.fi': ('Finland', 'Finland'),
    'kamera.trafikinfo.se': ('Sweden', 'Sweden'),
    'www.webcams.travel': ('Global', None),
    'webcams.travel': ('Global', None),
    'ristmikud.tallinn.ee': ('Estonia', 'Estonia'),
    'tallinn.ee': ('Estonia', 'Estonia'),
    'www.tallinn.ee': ('Estonia', 'Estonia'),
    'snowcam.crestedbutte-co.gov': ('Colorado', 'United States'),
    'ocfo.umich.edu': ('Michigan', 'United States'),
    'www.vail.com': ('Colorado', 'United States'),
    'coastalradar.gistda.or.th': ('Thailand', 'Thailand'),
    'gistda.or.th': ('Thailand', 'Thailand'),
    # South America
    'www.cmt.cl': ('Chile', 'Chile'),
    'www.uoct.cl': ('Chile', 'Chile'),
    'www.transitobogota.gov.co': ('Colombia', 'Colombia'),
    'www.seguridadvial.gob.ar': ('Argentina', 'Argentina'),
    # Oceania
    'www.livetraffic.com': ('Australia', 'Australia'),
    'livetraffic.com': ('Australia', 'Australia'),
    'www.qldtraffic.qld.gov.au': ('Queensland', 'Australia'),
    'www.livetraffic.nsw.gov.au': ('New South Wales', 'Australia'),
    'www.traffic.vic.gov.au': ('Victoria', 'Australia'),
    'www.transport.wa.gov.au': ('Western Australia', 'Australia'),
    'www.sa.gov.au': ('South Australia', 'Australia'),
    # Argentina/Chile/Mexico
    'sibys.seap.gov.ar': ('Argentina', 'Argentina'),
    'www.buenosaires.gob.ar': ('Buenos Aires', 'Argentina'),
    'www.c5.gob.mx': ('Mexico', 'Mexico'),
    'www.cdmx.gob.mx': ('Mexico City', 'Mexico'),
    'datos.cdmx.gob.mx': ('Mexico City', 'Mexico'),
    # Italy/Spain/France
    'www.autostrade.it': ('Italy', 'Italy'),
    'www.skylinewebcams.com': ('Italy', 'Italy'),
    'www.webcamtaxi.com': ('Italy', 'Italy'),
    'www.youwebcams.com': ('Italy', 'Italy'),
    'www.webcamera24.com': ('Germany', 'Germany'),
    # Other
    'www.ipcamlive.com': ('Global', None),
    'www.earthcam.com': ('United States', 'United States'),
    'earthcam.com': ('United States', 'United States'),
    'www.insecam.org': ('Global', None),
    'insecam.org': ('Global', None),
    'www.shodan.io': ('Global', None),
    'shodan.io': ('Global', None),
    'opensnow.com': ('United States', 'United States'),
    'snowforecast.com': ('United States', 'United States'),
    'www.mountaincams.com': ('Global', None),
    'www.peakbagger.com': ('Global', None),
    'www.snow-forecast.com': ('Global', None),
    'www.skiinfo.fr': ('France', 'France'),
    'www.skiinfo.it': ('Italy', 'Italy'),
    'www.onthesnow.com': ('United States', 'United States'),
    'www.resortcams.com': ('Global', None),
    # Public webcams/aggregators
    'webcams.travel:80': ('Global', None),
    'www.webcams.travel:80': ('Global', None),
    # News/weather
    'media-cdn.tripadvisor.com': ('Global', None),
    'www.tripadvisor.com': ('Global', None),
    'cf.bstatic.com': ('Global', None),
    'live.staticflickr.com': ('Global', None),
    'staticflickr.com': ('Global', None),
}

# Country name aliases
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
    'Éire': 'Ireland',
    'Eire': 'Ireland',
    'Magyarország': 'Hungary',
    'Cesko': 'Czech Republic',
    'Česko': 'Czech Republic',
    'Slovensko': 'Slovakia',
    'Hrvatska': 'Croatia',
    'Srbija': 'Serbia',
    'România': 'Romania',
    'Ελλάς': 'Greece',
    'Ελλάδα': 'Greece',
    'ישראל': 'Israel',
    'المغرب': 'Morocco',
    'مصر': 'Egypt',
}


def normalize_country(name):
    if not name:
        return None
    name = name.strip()
    if name in ALIASES:
        return ALIASES[name]
    return name


def get_tld_country(hostname):
    if not hostname:
        return None
    parts = hostname.lower().split('.')
    if len(parts) < 2:
        return None
    tld = parts[-1]
    if tld in CC_TLD:
        return CC_TLD[tld]
    if len(parts) >= 3:
        tld2 = parts[-2] + '.' + parts[-1]
        if tld2 in ('co.uk', 'org.uk', 'ac.uk', 'gov.uk', 'net.uk', 'ltd.uk', 'plc.uk'):
            return ('GB', 'United Kingdom')
        if tld2 in ('com.au', 'net.au', 'org.au', 'edu.au', 'gov.au', 'id.au'):
            return ('AU', 'Australia')
        if tld2 in ('co.jp', 'ne.jp', 'or.jp', 'ac.jp', 'go.jp', 'ad.jp', 'ed.jp'):
            return ('JP', 'Japan')
        if tld2 in ('co.kr', 'ne.kr', 'or.kr', 'go.kr', 'pe.kr'):
            return ('KR', 'South Korea')
        if tld2 in ('co.in', 'net.in', 'org.in', 'co.in', 'gen.in', 'firm.in'):
            return ('IN', 'India')
        if tld2 in ('co.nz', 'net.nz', 'org.nz', 'ac.nz', 'govt.nz'):
            return ('NZ', 'New Zealand')
        if tld2 in ('co.za', 'org.za', 'ac.za', 'net.za'):
            return ('ZA', 'South Africa')
        if tld2 in ('com.br', 'net.br', 'org.br', 'gov.br', 'edu.br'):
            return ('BR', 'Brazil')
        if tld2 in ('com.mx', 'org.mx', 'gob.mx'):
            return ('MX', 'Mexico')
        if tld2 in ('com.ar', 'org.ar', 'gov.ar'):
            return ('AR', 'Argentina')
        if tld2 in ('com.cn', 'org.cn', 'gov.cn', 'edu.cn', 'net.cn'):
            return ('CN', 'China')
        if tld2 in ('com.tw', 'org.tw', 'gov.tw', 'edu.tw', 'net.tw'):
            return ('TW', 'Taiwan')
        if tld2 in ('com.hk', 'org.hk', 'gov.hk', 'edu.hk', 'net.hk'):
            return ('HK', 'Hong Kong')
    return None


def get_host_geo(hostname):
    if not hostname:
        return None
    h = hostname.lower()
    # Direct match
    if h in HOST_GEO:
        return HOST_GEO[h]
    # Substring match for compound hosts
    for key, geo in HOST_GEO.items():
        if key in h:
            return geo
    return None


def extract_argus_source(notes):
    """Extract TV source name from argus_id in notes.
    argus_id format: opencctv_<source>_<id>-<num>
    """
    if not notes:
        return None
    m = re.search(r'argus_id=opencctv_(\w+?)_', notes)
    if m:
        return m.group(1)
    return None


def main():
    print("Loading TV catalog...", flush=True)
    t0 = time.time()
    with open(TV_CATALOG, 'r', encoding='utf-8') as f:
        tv = json.load(f)
    tv_cams = tv.get('cameras', [])
    print(f"  Loaded {len(tv_cams)} TV cams in {time.time()-t0:.1f}s", flush=True)

    # Build TV source -> dominant country
    print("Building TV source -> country index...", flush=True)
    t0 = time.time()
    tv_source_country = {}
    tv_source_geo = {}  # source -> (country, lat, lon)
    src_cams = defaultdict(list)
    for c in tv_cams:
        s = c.get('source', '')
        if s:
            src_cams[s].append(c)
    for src, cams in src_cams.items():
        # Find most common country
        country_counts = Counter()
        for c in cams:
            co = normalize_country(c.get('country', ''))
            if co:
                country_counts[co] += 1
        if country_counts:
            top_country = country_counts.most_common(1)[0][0]
            # Get sample lat/lon
            for c in cams:
                if c.get('lat') is not None and c.get('lng') is not None:
                    tv_source_geo[src] = (top_country, c['lat'], c['lng'])
                    break
            else:
                tv_source_geo[src] = (top_country, None, None)
            tv_source_country[src] = top_country
    print(f"  Built {len(tv_source_geo)} source->country mappings in {time.time()-t0:.1f}s", flush=True)

    # Read CSV
    print("Reading CSV...", flush=True)
    t0 = time.time()
    with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    print(f"  Read {len(rows)} rows in {time.time()-t0:.1f}s", flush=True)

    IDX = {col: i for i, col in enumerate(header)}
    COL_URL = IDX['url']
    COL_LIVE = IDX['live_stream_url']
    COL_COUNTRY = IDX['country']
    COL_REGION = IDX['region']
    COL_CITY = IDX['city']
    COL_LAT = IDX['lat']
    COL_LON = IDX['lon']
    COL_GEO_SRC = IDX['geo_source']
    COL_HOST = IDX['host']
    COL_NOTES = IDX['notes']

    stats = {
        'total': 0,
        'tv_source': 0,
        'host_geo': 0,
        'tld': 0,
        'unchanged': 0,
        'overwritten': 0,
        'no_signal': 0,
    }
    country_fixes = Counter()
    region_fixes = Counter()
    samples = []

    print("Processing rows...", flush=True)
    t0 = time.time()
    for i, row in enumerate(rows):
        if i % 10000 == 0 and i > 0:
            elapsed = time.time() - t0
            rate = i / elapsed
            print(f"  {i}/{len(rows)} ({rate:.0f}/s) {stats}", flush=True)
            with open(PROGRESS_PATH, 'w') as pf:
                cf_str = {f'{k[0]}|{k[1]}': v for k, v in country_fixes.items()}
                json.dump({'stats': dict(stats), 'last_idx': i, 'country_fixes': cf_str}, pf)

        stats['total'] += 1
        url = row[COL_URL] if COL_URL < len(row) else ''
        live = row[COL_LIVE] if COL_LIVE < len(row) else ''
        notes = row[COL_NOTES] if COL_NOTES < len(row) else ''
        old_country = row[COL_COUNTRY] if COL_COUNTRY < len(row) else ''
        old_region = row[COL_REGION] if COL_REGION < len(row) else ''
        old_city = row[COL_CITY] if COL_CITY < len(row) else ''
        old_lat = row[COL_LAT] if COL_LAT < len(row) else ''
        old_lon = row[COL_LON] if COL_LON < len(row) else ''

        # Find best host signal
        best_host = live or url
        hostname = ''
        if best_host:
            try:
                parsed = urlparse(best_host)
                hostname = (parsed.hostname or '').lower()
            except:
                pass

        new_country = None
        new_region = None
        new_lat = None
        new_lon = None
        source_used = None

        # 1. TV source from argus_id
        tv_src = extract_argus_source(notes)
        if tv_src and tv_src in tv_source_geo:
            new_country, new_lat, new_lon = tv_source_geo[tv_src]
            source_used = f'tv_src:{tv_src}'
            stats['tv_source'] += 1

        # 2. Host -> geo
        if not new_country and hostname:
            hg = get_host_geo(hostname)
            if hg and hg[1]:  # has country
                new_region, new_country = hg
                source_used = f'host:{hostname}'
                stats['host_geo'] += 1

        # 3. TLD
        if not new_country and hostname:
            tld = get_tld_country(hostname)
            if tld:
                new_country = tld[1]
                source_used = f'tld:{hostname.split(".")[-1]}'
                stats['tld'] += 1

        # Apply if we have new country and it's different from old
        if new_country and new_country != old_country:
            row[COL_COUNTRY] = new_country
            if new_region:
                row[COL_REGION] = new_region
            if new_lat is not None:
                row[COL_LAT] = str(new_lat)
            if new_lon is not None:
                row[COL_LON] = str(new_lon)
            row[COL_GEO_SRC] = source_used or 'rebuild_v2'
            stats['overwritten'] += 1
            country_fixes[(old_country, new_country)] += 1
            if len(samples) < 30:
                samples.append({
                    'idx': row[0],
                    'host': hostname,
                    'old': f'{old_country}/{old_region}/{old_city}',
                    'new': f'{new_country}/{new_region}',
                    'source': source_used
                })
        else:
            stats['unchanged'] += 1
            if not new_country:
                stats['no_signal'] += 1

    print(f"Processed {len(rows)} in {time.time()-t0:.1f}s", flush=True)
    print(f"Final stats: {stats}", flush=True)
    print(f"\nTop country fixes:")
    for (old, new), c in country_fixes.most_common(20):
        print(f"  {c:>6}  {old!r} -> {new!r}")
    print(f"\nSample fixes:")
    for s in samples[:20]:
        print(f"  idx={s['idx']} host={s['host']} {s['old']} -> {s['new']} via {s['source']}")

    # Write atomic
    print("\nWriting atomic CSV...", flush=True)
    tmp = CSV_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        w.writerow(header)
        for row in rows:
            w.writerow(row)
    os.replace(tmp, CSV_PATH)
    print(f"Done. Saved to {CSV_PATH}", flush=True)
    with open(PROGRESS_PATH, 'w') as pf:
        json.dump({'stats': dict(stats), 'country_fixes': dict(country_fixes), 'samples': samples, 'done': True}, pf)


if __name__ == '__main__':
    main()
