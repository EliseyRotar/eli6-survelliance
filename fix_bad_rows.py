"""
Fix the 22,544 bad rows from session27 ingestion (out-of-order columns).
Plan:
1. Read the bad rows (len 35)
2. Map each to a properly-ordered 37-col row by understanding which column
   the script put where
3. Delete the bad rows from CSV
4. Re-insert the proper 37-col rows
"""
import csv
from pathlib import Path

CSV_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')

# Expected header (37 columns)
EXPECTED_HEADER = [
    'idx', 'project_name', 'url', 'live_stream_url', 'type', 'auth_required',
    'auth_user', 'auth_pass', 'enabled', 'live_status', 'http_status', 'content_type',
    'server_header', 'page_title', 'description', 'category', 'likely_subject',
    'brand', 'model', 'country', 'region', 'city', 'zip', 'address', 'road',
    'location_precision', 'lat', 'lon', 'geo_source', 'isp', 'org', 'asn',
    'reverse_dns', 'host', 'confidence', 'notes', 'csv_id'
]
assert len(EXPECTED_HEADER) == 37

# The 35-col rows from session27 followed this pattern (looking at session27_ingest.py):
# [str(idx), name, url, live, type, 'False', '', '', 'True', 'live', '200', ct, '', '', desc, cat, subj, brand, model, country, region, city, '', address, lat, lng, geo_src, isp, org, '', '', host, conf, notes, csv_id]
# That's 35 columns. The original CSV had 35 cols but I added 2 (road, location_precision) AFTER column 24 (address).
# So my row was missing the 2 new fields. But the CSV is in WRONG order - because the WRITER used my row directly.
# Looking at row 212146, the 35 fields in order are:
# idx, project_name, url, live_stream_url, type, auth_required, auth_user, auth_pass, enabled, live_status, http_status, content_type, server_header, page_title, description, category, likely_subject, brand, model, country, region, city, zip, address, road(WRONG=lat), location_precision(WRONG=lon), lat(WRONG=geo_source), lon(WRONG=isp), geo_source(WRONG=org), isp(WRONG=asn), org(WRONG=reverse_dns), asn(WRONG=host), reverse_dns(WRONG=confidence), host(WRONG=notes), confidence(WRONG=csv_id)
# So the row got misaligned. The CSV writer wrote 35 fields under the 37-col header, causing 2 fields to be silently dropped from the END, and 2 fields to be at the wrong positions.
#
# Looking at row 212146: 'road': -2.333000 (this should be lat), 'location_precision': 34.834000 (this should be lon)
# So my row's lat/lng values were misaligned to road/location_precision, and the last 2 fields (notes, csv_id) were never written.
# In other words: the WRITER wrote my 35 fields under the 37-col header, which means:
#   - my idx -> idx
#   - my project_name -> project_name
#   - ... 33 fields aligned fine ...
#   - my address -> address (idx 24)
#   - my lat -> road (idx 25)  <-- WRONG
#   - my lon -> location_precision (idx 26)  <-- WRONG
#   - my geo_source -> lat (idx 27)  <-- WRONG
#   - my isp -> lon (idx 28)  <-- WRONG
#   - my org -> geo_source (idx 29)  <-- WRONG
#   - my asn -> isp (idx 30)  <-- WRONG
#   - my reverse_dns -> org (idx 31)  <-- WRONG
#   - my host -> asn (idx 32)  <-- WRONG
#   - my confidence -> reverse_dns (idx 33)  <-- WRONG
#   - my notes -> host (idx 34)  <-- WRONG
#   - my csv_id -> confidence (idx 35)  <-- WRONG
# Then the row only has 35 fields so notes (idx 36) and csv_id (idx 37) are missing from the row.
# But the WRITER pads with empty values? Or just stops at 35? Let me check.

# Actually looking at csv.writer - it just writes the fields you give it. If you give 35 fields, the row in CSV will be 35 fields. When DictReader reads it, it tries to match against the 37-col header, so the first 35 fields are mapped correctly, and the last 2 fields (notes, csv_id) are empty strings in the resulting dict.

# But wait - the file was APPENDED TO, so all old rows are still correct (37 fields), only my new rows are 35 fields.
# The "BAD row len=35" means csv.reader is reporting 35 fields for these rows.
# When DictReader reads, it sees 35 fields, and tries to map them to 37 columns. The first 35 get mapped, and the last 2 are missing.
# So in fact the row has: idx=name, name=url, ..., host=confidence, confidence=notes, notes=csv_id (WRONG MAPPINGS)
# All fields are shifted by 2 from where I intended.

# The recovery: for each bad row, the data is correct but mapped to wrong columns.
# I need to shift the data back: the value at column N was intended for column N-2 (because the last 2 fields "notes" and "csv_id" never got written).

# Wait, let me think again. The CSV has 37 columns header. My row has 35 values. csv.writer writes the 35 values into 35 columns. The LAST 2 columns (notes, csv_id) end up with no values - they exist in the header but not in any row. csv.reader will see 35 fields. DictReader will return empty for those 2 fields.

# But looking at the data: my 'road' field has -2.333000 (which was my LAT). So the WRITER wrote 35 values to 35 columns, but which columns? They were written in the order I gave them: idx, project_name, url, live_stream_url, type, auth_required, auth_user, auth_pass, enabled, live_status, http_status, content_type, server_header, page_title, description, category, likely_subject, brand, model, country, region, city, zip, address, lat, lon, geo_source, isp, org, asn, reverse_dns, host, confidence, notes, csv_id.
# So column 0=idx, 1=name, 2=url, 3=live, 4=type, 5=auth_req, 6=auth_user, 7=auth_pass, 8=enabled, 9=live_status, 10=http_status, 11=content_type, 12=server_header, 13=page_title, 14=description, 15=category, 16=likely_subject, 17=brand, 18=model, 19=country, 20=region, 21=city, 22=zip, 23=address, 24=lat, 25=lon, 26=geo_source, 27=isp, 28=org, 29=asn, 30=reverse_dns, 31=host, 32=confidence, 33=notes, 34=csv_id.
# The 37-col header has: ..., address(23), road(24), location_precision(25), lat(26), lon(27), geo_source(28), isp(29), org(30), asn(31), reverse_dns(32), host(33), confidence(34), notes(35), csv_id(36)
# So my values are shifted by 2: my value at position 24 (lat) is in CSV column 24 (road), my value at 25 (lon) is in 25 (location_precision), etc.

# So for recovery, I need to:
# 1. Read each bad row
# 2. Shift values: position 24-34 should be moved to positions 26-36 (insert 2 empty values at positions 24, 25 for road, location_precision)

# But to distinguish my rows from other rows that might be slightly short, let me identify them by source: the project_name starts with "AZ511 Cam ", "NY511 ", "Africam ", or "OCCTV "

# Let me write the recovery script:
GOOD_PREFIXES = ('AZ511 Cam ', 'NY511 ', 'Africam ', 'OCCTV ')

# Read all rows
with open(CSV_PATH, encoding='utf-8', newline='') as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = list(reader)

print(f'Header: {len(header)} columns')
print(f'Total rows: {len(rows)}')

# Identify bad rows (len 35 with our prefixes) and recover
fixed_rows = []
bad_count = 0
for row in rows:
    if len(row) == 35 and len(row) > 1 and row[1].startswith(GOOD_PREFIXES):
        # Bad row - fix it
        # Map: row[0..23] stays as-is, insert two empty values at 24,25, row[24..34] -> positions 26..36
        new_row = row[:24] + ['', ''] + row[24:]  # insert 2 empty for road, location_precision
        # Pad to 37 if needed
        while len(new_row) < 37:
            new_row.append('')
        fixed_rows.append(new_row[:37])
        bad_count += 1
    else:
        # Good row - keep as-is, pad to 37 if needed
        if len(row) < 37:
            row = row + [''] * (37 - len(row))
        fixed_rows.append(row[:37])

print(f'Fixed {bad_count} bad rows')
print(f'Final row count: {len(fixed_rows)}')

# Verify
ok_count = 0
still_bad = 0
for r in fixed_rows:
    if len(r) == 37:
        ok_count += 1
    else:
        still_bad += 1
print(f'Rows with correct length: {ok_count}')
print(f'Still bad: {still_bad}')

# Sample
print('\nSample fixed row (idx 212146):')
for r in fixed_rows:
    if r[0] == '212146':
        for k, v in zip(header, r):
            if v:
                print(f'  {k}: {v}')
        break

# Write back
with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(header)
    for row in fixed_rows:
        writer.writerow(row)
print(f'\nWrote {len(fixed_rows)} rows to {CSV_PATH}')
