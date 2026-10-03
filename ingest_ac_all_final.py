"""Final AC ingest: filter to live slugs, then append to CSV.
Uses existing 228,674 rows + 931 new AC cams = 229,605 total."""
import csv, sys
from pathlib import Path

csv_path = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')

# Load new review rows
with Path(r'C:\Users\eli6-admin\AppData\Local\Temp\ac_new_rows.csv').open(encoding='utf-8', newline='') as f:
    rdr = csv.DictReader(f)
    new_rows = list(rdr)

# Load liveness results
live_slugs = set()
with Path(r'C:\Users\eli6-admin\AppData\Local\Temp\ac_liveness.txt').open(encoding='utf-8') as f:
    for line in f:
        parts = line.strip().split('\t')
        if len(parts) == 3 and parts[1] == 'live':
            live_slugs.add(parts[0])
print(f'Live slugs: {len(live_slugs)}')

# Filter new rows to only live slugs
live_new_rows = []
for r in new_rows:
    slug = r['live_stream_url'].split('/public-camera-data/')[1].split('/')[0]
    if slug in live_slugs:
        live_new_rows.append(r)
print(f'Live new rows: {len(live_new_rows)}')

# Append to main CSV (no backup - we already backed up Session 37)
# Backup first
import shutil, datetime
backup_name = f'backup_20260915_{datetime.datetime.now().strftime("%H%M%S")}_session38a'
backup_path = csv_path.parent / 'backups' / backup_name
backup_path.mkdir(parents=True, exist_ok=True)
shutil.copy2(csv_path, backup_path / csv_path.name)
print(f'Backed up to {backup_path}')

# Read existing rows
with csv_path.open(encoding='utf-8', newline='') as f:
    rdr = csv.DictReader(f)
    fieldnames = rdr.fieldnames
    rows = list(rdr)
print(f'Existing rows: {len(rows)}')

# Renumber idx to avoid gaps (optional, but tidier)
# Actually keep idx as-is to avoid breaking external refs
# Just append

# Write back
all_rows = rows + live_new_rows
with csv_path.open('w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    for r in all_rows:
        w.writerow(r)
print(f'Wrote {len(all_rows)} rows to {csv_path} (was {len(rows)})')

# Save backup of ingest script
shutil.copy2(Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\ingest_ac_all.py'),
             backup_path / 'ingest_ac_all.py')
shutil.copy2(Path(r'C:\Users\eli6-admin\AppData\Local\Temp\ac_new_rows.csv'),
             backup_path / 'ac_new_rows.csv')
shutil.copy2(Path(r'C:\Users\eli6-admin\AppData\Local\Temp\ac_liveness.txt'),
             backup_path / 'ac_liveness.txt')
