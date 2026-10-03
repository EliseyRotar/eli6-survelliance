"""
Update the 12 existing SATAP A4 cams (idx 129968-129979) with better metadata
from A4-punti.js, then delete the duplicate 12 (idx 212122-212133) we just added.
"""
import csv
import json
from pathlib import Path

CSV_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')
MARKER_PATH = Path(r'C:\Users\eli6-admin\AppData\Local\Temp\opencode\A4-marker.json')

with open(MARKER_PATH, encoding='utf-8') as f:
    data = json.load(f)

# Build a lookup by info (cam ID) - info is int
cams_by_id = {str(c['info']): c for c in data['webcam']}

# Map: existing CSV idx -> SATAP info id
EXISTING_TO_INFO = {
    129968: '1147',  # Torino
    129969: '1109',  # Volpiano
    129970: '1130',  # Chivasso Est
    129971: '1102',  # Rondissone
    129972: '1121',  # Borgo D'Ale
    129973: '1124',  # Carisio
    129974: '1126',  # Villarboit
    129975: '1113',  # Biandrate
    129976: '1117',  # Novara Ovest
    129977: '1119',  # Novara Est
    129978: '1107',  # Marcallo
    129979: '1148',  # Milano
}

# Read CSV
with open(CSV_PATH, encoding='utf-8', newline='') as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = list(reader)

print(f"Loaded {len(rows)} rows")

updated_count = 0
deleted_count = 0
new_rows = []
for row in rows:
    if not row[0].isdigit():
        # Garbled row from old session - keep as-is
        new_rows.append(row)
        continue
    idx = int(row[0])
    # Delete my new 12 duplicates
    if 212122 <= idx <= 212133:
        deleted_count += 1
        continue
    # Update existing 12 SATAP cams
    if idx in EXISTING_TO_INFO:
        info = EXISTING_TO_INFO[idx]
        c = cams_by_id[info]
        descriz = c['descriz']  # e.g. "Torino KM 0+050"
        lat = c['lat']
        lng = c['lng']
        video_url = c['video']
        poster_url = c['url']
        parts = descriz.split(' KM ', 1)
        city = parts[0] if len(parts) > 0 else descriz
        road_ref = 'KM ' + parts[1] if len(parts) > 1 else ''
        # Update key fields (keep most of original metadata)
        # idx(0), project_name(1), url(2), live_stream_url(3), type(4),
        # auth_required(5), auth_user(6), auth_pass(7), enabled(8),
        # live_status(9), http_status(10), content_type(11), server_header(12),
        # page_title(13), description(14), category(15), likely_subject(16),
        # brand(17), model(18), country(19), region(20), city(21),
        # zip(22), address(23), lat(24), lon(25), geo_source(26),
        # isp(27), org(28), asn(29), reverse_dns(30), host(31),
        # confidence(32), notes(33), csv_id(34)
        row[1] = f"SATAP A4 {descriz}"  # project_name
        row[2] = "https://www.satapweb.it/mappa-interattiva-a4/"  # url (homepage, was duplicate of live)
        row[4] = "mp4"  # type (was 'video')
        # Add region for the ones missing it
        if not row[20]:
            row[20] = "Piedmont/Lombardy"
        # Set city
        if not row[21]:
            row[21] = city
        # Set address
        if not row[23] or row[23] == row[21]:
            row[23] = f"A4 {road_ref}, {city}"
        # Update lat/lng to precise A4-punti.js coords
        row[24] = str(lat)
        row[25] = str(lng)
        row[26] = "satap_a4_marker"  # geo_source
        # Update notes to include both sources + poster
        existing_notes = row[33] if len(row) > 33 else ''
        new_notes = f"precise lat/lng from A4-punti.js; poster={poster_url}; {existing_notes}"
        if len(new_notes) > 500:
            new_notes = new_notes[:497] + "..."
        row[33] = new_notes
        updated_count += 1
    new_rows.append(row)

print(f"Updated: {updated_count}")
print(f"Deleted: {deleted_count}")
print(f"Final row count: {len(new_rows)}")

# Write back
with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(header)
    for row in new_rows:
        writer.writerow(row)

print("CSV updated successfully")
