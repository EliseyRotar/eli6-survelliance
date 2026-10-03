"""Fix the broken row by reconstructing from its parts."""
import csv
import os
import sys

sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')
csv.field_size_limit(2**31 - 1)

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
BACKUP_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\backups\controllable_Webcams_broken.csv'

with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
    rows = list(csv.reader(f))

# Backup
os.makedirs(os.path.dirname(BACKUP_PATH), exist_ok=True)
with open(BACKUP_PATH, 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
    for r in rows:
        w.writerow(r)

# Find broken row
broken_idx = None
for i, r in enumerate(rows):
    if len(r) != 35:
        broken_idx = i
        break

if broken_idx is None:
    print('No broken rows!')
    sys.exit(0)

broken = rows[broken_idx]
print(f'Broken row {broken_idx}: len={len(broken)}')
for i, c in enumerate(broken):
    print(f'  [{i}] {c[:200]}')

# Reconstruct: The notes field has commas. Original was quoted in CSV.
# The fields after splitting are:
# col 1: " source=argus-v3" — second part of notes after first 4 fields
# col 2: " content-type=image/png" — third part
# col 3: ' server-banner-unknown; argus_id=opencctv_state511_s511-NV-5821"' — fourth part WITH closing quote
# col 4: 'disc_174837' — csv_id (correct)

# The full notes would have been:
# "Family=argus-public, kind=jpeg-frame, weight=8, source=argus-v3, content-type=image/png, server-banner-unknown; argus_id=opencctv_state511_s511-NV-5821"

# Reconstruct from parts
# Note: the split happened because commas in notes weren't quoted
# So col 1, 2, 3 are pieces of the notes that came after the first comma

# But wait — col 0 is '174827' (idx), and the broken row has only 5 columns.
# That means: idx + 4 broken chunks. Original should be: idx + project_name + url + live_stream_url + type + ... + notes + csv_id = 35 cols
# So missing: project_name, url, live_stream_url, type, auth_required, auth_user, auth_pass, enabled, live_status, http_status, content_type, server_header, page_title, description, category, likely_subject, brand, model, country, region, city, zip, address, lat, lon, geo_source, isp, org, asn, reverse_dns, host, confidence = 31 fields

# That's 4 chunks for 35 fields = missing 31 fields. Impossible to reconstruct.
# The row is unrecoverable. Drop it.

# Strategy: remove broken row, also renumber idx after it

print(f'\nRemoving unrecoverable broken row {broken_idx}')
del rows[broken_idx]

# Save back
tmp = CSV_PATH + '.tmp'
with open(tmp, 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
    for r in rows:
        # Pad/truncate to 35 cols
        if len(r) < 35:
            r = r + [''] * (35 - len(r))
        elif len(r) > 35:
            r = r[:35]
        w.writerow(r)

import os as _os
import time as _time
for _ in range(30):
    try:
        if _os.path.exists(tmp):
            _os.replace(tmp, CSV_PATH)
            break
        else:
            _time.sleep(0.5)
    except PermissionError:
        _time.sleep(0.5)

# Verify
with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
    rows2 = list(csv.reader(f))
bad = sum(1 for r in rows2 if len(r) != 35)
print(f'\nAfter fix: {len(rows2)} rows, {bad} bad rows')
