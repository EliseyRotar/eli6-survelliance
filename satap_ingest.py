"""
Ingest SATAP A4 Italian tollway webcams (12 cams, MP4 video files) into the CSV.
"""
import csv
import json
from pathlib import Path

CSV_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')
MARKER_PATH = Path(r'C:\Users\eli6-admin\AppData\Local\Temp\opencode\A4-marker.json')

with open(MARKER_PATH, encoding='utf-8') as f:
    data = json.load(f)

webcams = data['webcam']
print(f"Found {len(webcams)} SATAP A4 webcams")

# Read existing CSV to get last idx
with open(CSV_PATH, encoding='utf-8', newline='') as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = list(reader)

# Find max idx (skip non-numeric entries from any garbled rows in the CSV)
max_idx = max((int(r[0]) for r in rows if r[0].isdigit()), default=0)
print(f"Current max idx: {max_idx}")
start_idx = max_idx + 1
print(f"Adding new rows starting at idx {start_idx}")

# Build new rows
new_rows = []
for i, c in enumerate(webcams):
    idx = start_idx + i
    info = c['info']
    descriz = c['descriz']  # e.g. "Torino KM 0+050"
    lat = c['lat']
    lng = c['lng']
    video_url = c['video']  # MP4
    poster_url = c['url']  # JPG

    # Parse name: "Torino KM 0+050" -> name=Torino, road_ref=KM 0+050
    parts = descriz.split(' KM ', 1)
    city = parts[0] if len(parts) > 0 else descriz
    road_ref = 'KM ' + parts[1] if len(parts) > 1 else ''

    # CSV columns:
    # 0  idx
    # 1  project_name
    # 2  url (homepage, used as fallback for static cams)
    # 3  live_stream_url (the actual stream)
    # 4  type (mp4, hls, image, mjpeg, etc.)
    # 5  auth_required
    # 6  auth_user
    # 7  auth_pass
    # 8  enabled
    # 9  live_status
    # 10 http_status
    # 11 content_type
    # 12 server_header
    # 13 page_title
    # 14 description
    # 15 category
    # 16 likely_subject
    # 17 brand
    # 18 model
    # 19 country
    # 20 region
    # 21 city
    # 22 zip
    # 23 address
    # 24 lat
    # 25 lon
    # 26 geo_source
    # 27 isp
    # 28 org
    # 29 asn
    # 30 reverse_dns
    # 31 host
    # 32 confidence
    # 33 notes
    # 34 csv_id

    row = [
        str(idx),                                # idx
        f"SATAP A4 {descriz}",                   # project_name
        "https://www.satapweb.it/mappa-interattiva-a4/",  # url (homepage)
        video_url,                               # live_stream_url
        "mp4",                                   # type
        "False",                                 # auth_required
        "",                                      # auth_user
        "",                                      # auth_pass
        "True",                                  # enabled
        "live",                                  # live_status
        "200",                                   # http_status
        "video/mp4",                             # content_type
        "",                                      # server_header
        f"SATAP A4 webcam - {descriz}",          # page_title
        f"SATAP A4 Italian tollway live webcam at {descriz}. Real-time MP4 video (server overwrites every ~30s).",  # description
        "traffic",                               # category
        "Live public camera",                    # likely_subject
        "SATAP",                                 # brand
        "A4 webcam",                             # model
        "Italy",                                 # country
        "Piedmont/Lombardy",                     # region
        city,                                    # city
        "",                                      # zip
        f"A4 {road_ref}, {city}",                # address
        str(lat),                                # lat
        str(lng),                                # lon
        "satap",                                 # geo_source
        "SATAP S.p.A.",                          # isp
        "SATAP A4 Torino-Milano",                # org
        "",                                      # asn
        "",                                      # reverse_dns
        "www.satapweb.it",                       # host
        "high",                                  # confidence
        f"SATAP A4 webcam [{info}] - MP4 looping clip overwritten on server every ~30s. Poster: {poster_url}",  # notes
        f"satap_{info}",                         # csv_id
    ]
    new_rows.append(row)

# Append to CSV
with open(CSV_PATH, 'a', encoding='utf-8', newline='') as f:
    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
    for row in new_rows:
        writer.writerow(row)

print(f"Appended {len(new_rows)} rows to CSV. New max idx: {start_idx + len(new_rows) - 1}")
print(f"\nFirst new row (idx {start_idx}):")
print(','.join(new_rows[0][:8]) + ',...')
print(f"\nLast new row (idx {start_idx + len(new_rows) - 1}):")
print(','.join(new_rows[-1][:8]) + ',...')
