"""
Update existing kenyawebcam cams in CSV with proper region/city/altitude metadata
from the parsed kenyawebcam_cams.json.
"""
import csv
import json
from pathlib import Path

CSV_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')
KW_CAMS_PATH = Path(r'C:\Users\eli6-admin\AppData\Local\Temp\opencode\kenyawebcam_cams.json')

with open(KW_CAMS_PATH, encoding='utf-8') as f:
    kw_cams = json.load(f)
by_slug = {c['slug']: c for c in kw_cams}

# Read CSV
with open(CSV_PATH, encoding='utf-8', newline='') as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = list(reader)

updated = 0
not_found = set()
for row in rows:
    if not row[0].isdigit():
        continue
    combined = (row[1] if len(row) > 1 else '') + ' ' + (row[2] if len(row) > 2 else '') + ' ' + (row[3] if len(row) > 3 else '')
    matched_slug = None
    for slug, c in by_slug.items():
        if f'/{slug}/' in combined and 'kenyawebcam' in combined.lower():
            matched_slug = slug
            break
    if not matched_slug:
        continue
    c = by_slug[matched_slug]
    # idx(0), project_name(1), url(2), live_stream_url(3), type(4),
    # auth_required(5), auth_user(6), auth_pass(7), enabled(8),
    # live_status(9), http_status(10), content_type(11), server_header(12),
    # page_title(13), description(14), category(15), likely_subject(16),
    # brand(17), model(18), country(19), region(20), city(21),
    # zip(22), address(23), lat(24), lon(25), geo_source(26),
    # isp(27), org(28), asn(29), reverse_dns(30), host(31),
    # confidence(32), notes(33), csv_id(34)
    region = c['region']
    location = c['location']
    # Update region if missing or generic
    if not row[20] or row[20] in ('', 'Kenya'):
        row[20] = region
    # Update city if missing
    if not row[21]:
        # Use first part of location (before " - ")
        city = location.split(' - ')[0] if ' - ' in location else location
        row[21] = city
    # Update org
    if not row[28] or 'webcamtaxi' in row[28].lower() or 'argus' in row[28].lower():
        row[28] = f"Kenyawebcam.com ({region})"
    # Update lat/lng if approximated (and the cam currently has bad/generic coords)
    try:
        current_lat = float(row[24])
        current_lng = float(row[25])
    except (ValueError, IndexError):
        current_lat = current_lng = None
    if current_lat is None or (current_lat == 0.0 and current_lng == 0.0) or c.get('geo_source') == 'html_dms':
        row[24] = f"{c['lat']:.6f}"
        row[25] = f"{c['lng']:.6f}"
        row[26] = c.get('geo_source', 'approximated_from_region')
    # Add altitude/direction to notes if not present
    notes = row[33] if len(row) > 33 else ''
    if c.get('altitude_ft') and 'altitude_ft=' not in notes:
        existing = notes
        new = f"altitude_ft={c['altitude_ft']}; direction={c.get('direction', '')}; {existing}"
        if len(new) > 500:
            new = new[:497] + '...'
        row[33] = new
    updated += 1

print(f"Updated {updated} existing kenyawebcam rows")

# Write back
with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)

print("CSV saved")
