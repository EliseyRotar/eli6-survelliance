"""
PHASE 3: Master Ingestion Script (FIXED with 37 columns)

Ingests all 4 sources into the CSV:
- AZ511: 644 cams (JPEG-only, no live available)
- 511 NY: ~1,800 cams (80% HLS, 20% static JPEG)
- Africam worldwide: 34 cams (YouTube embeds)

CSV has 37 columns: idx, project_name, url, live_stream_url, type, auth_required,
auth_user, auth_pass, enabled, live_status, http_status, content_type, server_header,
page_title, description, category, likely_subject, brand, model, country, region, city,
zip, address, road, location_precision, lat, lon, geo_source, isp, org, asn,
reverse_dns, host, confidence, notes, csv_id
"""
import csv, json
from pathlib import Path

CSV_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')
TEMP_DIR = Path(r'C:\Users\eli6-admin\AppData\Local\Temp\opencode')

# Find max idx
with open(CSV_PATH, encoding='utf-8', newline='') as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = list(reader)
max_idx = max((int(r[0]) for r in rows if r[0].isdigit()), default=0)
print(f"Current max idx: {max_idx}")
start_idx = max_idx + 1
print(f"Header cols: {len(header)}")

# Helpers
def s(v):
    return (v or '').strip() if v else ''

# ====== AFRICAM 34 NEW WORLDWIDE YOUTUBE CAMPS ======
AFRICAM_NEW = [
    # Tanzania
    ('Elewana Serengeti Explorer Live', 'Serengeti, Mara', 'Serengeti', 'Tanzania', -2.333, 34.834, 'BmOLK7LTKbY', 'serengeti', 'Live from the Serengeti'),
    # Namibia
    ('Onguma The Fort Waterhole Cam', 'Onguma, Etosha', 'Etosha', 'Namibia', -19.0, 15.917, 'yuIm1V7Ne7I', 'onguma', 'LIVE: Onguma Waterhole'),
    ('Safarihoek Live Wildlife Cam', 'Etosha Heights', 'Etosha Heights', 'Namibia', -19.5, 15.833, 'kMl8ST21Yt8', 'safarihoek', 'Live Wildlife Camera At Safarihoek'),
    # Zimbabwe
    ('Deteema Springs Live Cam', 'Hwange National Park', 'Hwange', 'Zimbabwe', -19.0, 26.5, 'm4cAV-_7YpY', 'deteemasprings', 'LIVE from Deteema Springs'),
    ('The Hide Hwange Live Cam', 'Hwange National Park', 'Hwange', 'Zimbabwe', -19.0, 26.5, 'nXI-kWu6BLo', 'thehide', 'Live Wildlife Camera at The Hide'),
    ('Wilderness Linkwasha Live Cam', 'Hwange National Park', 'Hwange', 'Zimbabwe', -19.0, 26.5, '-rXriX4SiQk', 'linkwasha', 'Wilderness Linkwasha LIVE Cam'),
    ('Hwange Safari Lodge Live Cam', 'Hwange National Park', 'Hwange', 'Zimbabwe', -19.0, 26.5, 'DhCfRI7XssU', 'hwange', 'Hwange Safari Lodge - Live'),
    ('Tembo Plains Live Cam', 'Sapi Private Reserve', 'Sapi Reserve', 'Zimbabwe', -15.85, 29.95, 'jH3e5w4BWGA', 'temboplains', 'LIVE from the Zambezi River'),
    ('Victoria Falls Safari Live', 'Victoria Falls', 'Victoria Falls', 'Zimbabwe', -17.925, 25.857, 'f9uqHbXChno', 'vicfalls', 'Vic Falls Live Waterhole Cam'),
    # Botswana
    ('Senyati Safari Camp Live', 'Chobe', 'Chobe', 'Botswana', -18.5, 24.0, 'EdDdTrahHjI', 'senyati', 'Senyati Waterhole LIVE'),
    ('Kalahari Salt Pan Live', 'Makgadikgadi Pans', 'Makgadikgadi', 'Botswana', -20.5, 25.5, 'ZVRUiKmCs84', 'kalahari', 'Kalahari Salt Pan Conservation Live'),
    ('Twin Pan Zarafa Camp Live', 'Selinda Reserve', 'Selinda', 'Botswana', -19.0, 23.5, '2EZavJUNdLI', 'twinpan', 'Twin Pan Live Hide Cam'),
    ('The Basin Selinda Camp Live', 'Selinda Reserve', 'Selinda', 'Botswana', -19.0, 23.5, 'vEEGzyCvL8Q', 'thebasin', 'The Basin Live Hide Cam'),
    ("Jack's Camp Live", 'Makgadikgadi Pans', 'Makgadikgadi', 'Botswana', -20.5, 25.5, 'jG0uYl5S44E', 'jackscamp', "Live from Jack's Camp"),
    ('Meno a Kwena Live', 'Boteti River', 'Boteti', 'Botswana', -20.5, 24.0, 'RZFMYVNhd4k', 'meno', 'LIVE: Zebra Migration at Meno a Kwena'),
    ('Camelthorn Live Cam', 'Boteti River', 'Boteti', 'Botswana', -20.5, 24.0, 'mk02pEy3FdA', 'camelthorn', 'Camelthorn Waterhole Live'),
    ('Moela Lodge Live', 'Boteti River', 'Boteti', 'Botswana', -20.5, 24.0, '54Y7xlLrkuo', 'moela', 'Moela Safari Lodge LIVE'),
    ('Elephant Pan Live', 'Khwai Private Reserve', 'Khwai', 'Botswana', -19.0, 23.5, 'QJe1tGI1EZc', 'elephantpan', 'Elephant Pan - Live Wildlife Camera'),
    # South Africa
    ('Ulusaba Live Cam', 'Sabi Sand', 'Sabi Sand', 'South Africa', -24.766, 31.5, 'zqc0Z2oWmo8', 'ulusaba', 'Ulusaba Live Wildlife Camera'),
    ('Black Eagle Nest Live', 'Selati Game Reserve', 'Selati', 'South Africa', -23.5, 30.0, 'xsiM3-M5bmo', 'blackeagle', 'LIVE Black Eagle Nest Cam 2026'),
    ('HESC Live Cam', 'Hoedspruit', 'Hoedspruit', 'South Africa', -24.35, 30.95, 'YhXWGJQtEQY', 'hesc', '24/7 Live: Rhino Orphans at HESC'),
    ('Penguins Stony Point Live', 'Stony Point', 'Stony Point', 'South Africa', -34.367, 18.883, 'NiwrvhQIHIo', 'penguins', 'Watch African Penguins LIVE'),
    ('Lesser Flamingos Kamfers Dam Live', 'Kimberley', 'Kamfers Dam', 'South Africa', -29.667, 18.5, 'IdDorfgnATw', 'flamingos', 'Kamfers Dam | Flamingos 24/7'),
    ('Serondella Live', 'Thornybush Game Reserve', 'Thornybush', 'South Africa', -24.5, 31.2, 'BMQifTcOgts', 'serondella', 'Serondella | LIVE Wildlife Camera'),
    ('Kings Camp Live', 'Timbavati Game Reserve', 'Timbavati', 'South Africa', -24.0, 31.25, '_AyumoafMOU', 'kingscamp', "Kings Camp | Live Wildlife Stream"),
    ('Nkorho Bush Lodge Live', 'Sabi Sand', 'Sabi Sand', 'South Africa', -24.766, 31.5, 'sQAhSkjRKGk', 'nkorho', 'Live Safari from Nkorho'),
    ('Silvan Safari Live', 'Sabi Sand', 'Sabi Sand', 'South Africa', -24.766, 31.5, 'C9hjksOtngo', 'silvan', "Roy's Dam LIVE Cam"),
    ('Simbavati Waterside Live', 'Klaserie', 'Klaserie', 'South Africa', -24.0, 31.25, 'zh5QHh9prA0', 'simbavati', 'Simbavati Waterside Live'),
    ('Tembe Elephant Park Live', 'Maputaland', 'Maputaland', 'South Africa', -27.0, 32.5, 'gdrNUUf-cQw', 'tembe', 'Tembe Elephant Park | Wildlife Live'),
    ('Tau Game Lodge Live', 'Madikwe', 'Madikwe', 'South Africa', -24.75, 26.4, '8J9USywkGmw', 'tau', 'Tau Game Lodge | Wildlife Live'),
    ('Kwa Maritane Live', 'Pilanesberg', 'Pilanesberg', 'South Africa', -25.25, 27.083, 'aWglOXp5id0', 'kwamaritane', 'Africam - Kwa Maritane'),
    ('Kruger Shalati Live', 'Kruger National Park', 'Kruger', 'South Africa', -24.5, 31.5, '0mmIsIZXJx4', 'krugershalati', 'Kruger Shalati Bridge View LIVE'),
    ('Jabulani Safari Lodge Live', 'Kapama', 'Kapama', 'South Africa', -24.45, 31.0, '8JzwlpcVyKM', 'jabulani', 'Jabulani: Live Wildlife Stream'),
    ('Founders Lodge Live', 'Eastern Cape', 'Eastern Cape', 'South Africa', -33.5, 26.5, 'LaicUirnDJ4', 'founders', 'Founders Lodge By Mantis | Wildlife Live'),
]
print(f"Africam new worldwide: {len(AFRICAM_NEW)} cams")

# Build a row template based on actual header
# Order MUST match: idx, project_name, url, live_stream_url, type, auth_required, auth_user, auth_pass, enabled, live_status, http_status, content_type, server_header, page_title, description, category, likely_subject, brand, model, country, region, city, zip, address, road, location_precision, lat, lon, geo_source, isp, org, asn, reverse_dns, host, confidence, notes, csv_id

new_rows = []
idx = start_idx

# 1) AFRICAM YOUTUBE
for name, loc, region, country, lat, lng, yt_id, slug, desc in AFRICAM_NEW:
    yt_url = f'https://www.youtube.com/watch?v={yt_id}'
    city = loc.split(',')[0].strip()
    row = [
        str(idx),                           # idx
        f"Africam {name}",                  # project_name
        yt_url,                              # url (homepage)
        yt_url,                              # live_stream_url
        "youtube",                           # type
        "False",                             # auth_required
        "",                                  # auth_user
        "",                                  # auth_pass
        "True",                              # enabled
        "live",                              # live_status
        "200",                               # http_status
        "text/html; charset=utf-8",          # content_type
        "",                                  # server_header
        desc,                                # page_title
        f"Africam YouTube live stream - {region}, {country}. {desc}",  # description
        "scenic",                            # category
        "Live public camera",                # likely_subject
        "Africam",                           # brand
        "Wildlife live stream",              # model
        country,                             # country
        region,                              # region
        city,                                # city
        "",                                  # zip
        f"{loc}, {country}",                 # address
        "",                                  # road
        "",                                  # location_precision
        f"{lat:.6f}",                        # lat
        f"{lng:.6f}",                        # lon
        "africa_wildlife_gis",               # geo_source
        "Africam (WildEarth)",               # isp
        f"Africam ({region})",               # org
        "",                                  # asn
        "",                                  # reverse_dns
        "youtube.com",                       # host
        "high",                              # confidence
        f"africam_lodge={slug}; yt_id={yt_id}; yt_title={desc}",  # notes
        f"africam_{yt_id}",                  # csv_id
    ]
    assert len(row) == 37, f"Africam row has {len(row)} cols, expected 37"
    new_rows.append(row)
    idx += 1
print(f"  -> {len(AFRICAM_NEW)} Africam YouTube rows")

# 2) AZ511 (JPEG only - no live stream exists)
az_path = TEMP_DIR / 'az511-cams.json'
if az_path.exists():
    with open(az_path, encoding='utf-8') as f:
        az_data = json.load(f)
    az_cams = az_data.get('item2', [])
    az_count = 0
    for c in az_cams:
        sid = c['itemId']
        lat, lng = c['location'][0], c['location'][1]
        url = f"https://www.az511.com/map/Cctv/{sid}"
        row = [
            str(idx),                            # 0 idx
            f"AZ511 Cam {sid}",                  # 1 project_name
            "https://www.az511.com/map/",        # 2 url
            url,                                  # 3 live_stream_url
            "image",                              # 4 type
            "False",                              # 5 auth_required
            "",                                   # 6 auth_user
            "",                                   # 7 auth_pass
            "True",                               # 8 enabled
            "live",                               # 9 live_status
            "200",                                # 10 http_status
            "image/jpeg",                         # 11 content_type
            "",                                   # 12 server_header
            "",                                   # 13 page_title
            f"Arizona DOT 511 traffic camera {sid} - static JPEG snapshot, refreshes every 1-5 minutes (no live video available)",  # 14 description
            "traffic",                            # 15 category
            "Live public camera",                 # 16 likely_subject
            "ADOT (Arizona DOT)",                 # 17 brand
            "511 traffic cam",                    # 18 model
            "United States",                      # 19 country
            "Arizona",                            # 20 region
            "",                                   # 21 city
            "",                                   # 22 zip
            f"AZ DOT traffic cam {sid}",          # 23 address
            "",                                   # 24 road
            "",                                   # 25 location_precision
            f"{lat:.6f}",                         # 26 lat
            f"{lng:.6f}",                         # 27 lon
            "az511_official",                     # 28 geo_source
            "Arizona Department of Transportation",  # 29 isp
            "ADOT 511",                           # 30 org
            "",                                   # 31 asn
            "",                                   # 32 reverse_dns
            "www.az511.com",                      # 33 host
            "high",                               # 34 confidence
            f"az511_id={sid}; type=image; note=no live stream (ADOT disabled)",  # 35 notes
            f"az511_{sid}",                       # 36 csv_id
        ]
        if len(row) != 37:
            print(f"DEBUG row len={len(row)}:")
            for i, v in enumerate(row):
                print(f"  [{i}] = {v[:60]!r}")
        assert len(row) == 37, f"AZ511 row has {len(row)} cols, expected 37"
        new_rows.append(row)
        idx += 1
        az_count += 1
    print(f"  -> {az_count} AZ511 rows")

# 3) 511 NY (1,866 cams; 80% HLS, 20% static)
ny_path = TEMP_DIR / '511ny_tooltips_v3.json'
if not ny_path.exists():
    ny_path = TEMP_DIR / '511ny_tooltips_v2.json'
if not ny_path.exists():
    ny_path = TEMP_DIR / '511ny_tooltips.json'
if ny_path.exists():
    with open(ny_path, encoding='utf-8') as f:
        ny_data = json.load(f)
    ny_by_id = {r['site_id']: r for r in ny_data}

    ny_cams_path = TEMP_DIR / '511ny_cameras.json'
    with open(ny_cams_path, encoding='utf-8') as f:
        ny_cams_all = json.load(f)['item2']

    hls_count = 0
    static_count = 0
    err_count = 0
    for c in ny_cams_all:
        sid = c['itemId']
        lat, lng = c['location'][0], c['location'][1]
        tip = ny_by_id.get(sid, {})
        if 'error' in tip or not tip.get('image_id'):
            err_count += 1
            continue
        img_id = tip['image_id']
        name = tip.get('cam_name') or f'NY511 Cam {sid}'
        video_url = tip.get('video_url')
        img_url = f"https://511ny.org/map/Cctv/{img_id}"
        if video_url and '.m3u8' in video_url:
            cam_type = 'hls'
            live = video_url
            hls_count += 1
        else:
            cam_type = 'image'
            live = img_url
            static_count += 1
        row = [
            str(idx),                            # 0 idx
            f"NY511 {name}",                      # 1 project_name
            "https://511ny.org/map/",             # 2 url
            live,                                  # 3 live_stream_url
            cam_type,                              # 4 type
            "False",                               # 5 auth_required
            "",                                    # 6 auth_user
            "",                                    # 7 auth_pass
            "True",                                # 8 enabled
            "live",                                # 9 live_status
            "200",                                 # 10 http_status
            "video/mp4" if cam_type == 'hls' else "image/jpeg",  # 11 content_type
            "",                                    # 12 server_header
            name,                                  # 13 page_title
            f"NY 511 traffic camera at {name} - {'live HLS video' if cam_type == 'hls' else 'static JPEG refresh'}",  # 14 description
            "traffic",                             # 15 category
            "Live public camera",                  # 16 likely_subject
            "NYSDOT",                              # 17 brand
            "511 traffic cam",                     # 18 model
            "United States",                       # 19 country
            "New York",                            # 20 region
            "",                                    # 21 city
            "",                                    # 22 zip
            f"NY 511 Cam {sid}",                  # 23 address
            "",                                    # 24 road
            "",                                    # 25 location_precision
            f"{lat:.6f}",                          # 26 lat
            f"{lng:.6f}",                          # 27 lon
            "511ny_official",                      # 28 geo_source
            "New York State Department of Transportation",  # 29 isp
            "NYSDOT 511",                          # 30 org
            "",                                    # 31 asn
            "511ny.org",                           # 32 reverse_dns
            "511ny.org",                           # 33 host
            "high",                                # 34 confidence
            f"511ny_site_id={sid}; 511ny_image_id={img_id}; type={cam_type}",  # 35 notes
            f"511ny_{sid}",                        # 36 csv_id
        ]
        if len(row) != 37:
            print(f"DEBUG row len={len(row)}:")
            for i, v in enumerate(row):
                print(f"  [{i}] = {v[:60]!r}")
        assert len(row) == 37, f"NY511 row has {len(row)} cols, expected 37"
        new_rows.append(row)
        idx += 1
    print(f"  -> 511 NY: {hls_count} HLS + {static_count} static + {err_count} skipped")

# Write to CSV
print(f"\nTotal new rows: {len(new_rows)}")
print(f"New max idx: {idx - 1}")

with open(CSV_PATH, 'a', encoding='utf-8', newline='') as f:
    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
    for row in new_rows:
        writer.writerow(row)
print(f"Appended to {CSV_PATH}")
