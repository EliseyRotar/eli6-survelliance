"""Remove dead cams from CSV (they're already in quarantine)."""
import csv
import os
import sys
import time
import random

sys.stdout.reconfigure(line_buffering=True)

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
DEAD_CSV = r'C:\Users\eli6-admin\Documents\eli6-surveillance\data\dead_cams_quarantine.csv'

print(f'Loading {CSV_PATH}...', flush=True)
csv.field_size_limit(2**31-1)
with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    header = reader.fieldnames
print(f'  {len(rows):,} rows', flush=True)

# Filter out dead cams
alive_rows = []
n_dead = 0
for row in rows:
    if row.get('live_status') == 'dead':
        n_dead += 1
    else:
        alive_rows.append(row)

print(f'  Alive: {len(alive_rows):,}, Dead to remove: {n_dead:,}', flush=True)

if n_dead == 0:
    print('Nothing to remove', flush=True)
    sys.exit(0)

# Save with retry - write in chunks if large
tmp = CSV_PATH + '.tmp'
chunk_size = 10000
for attempt in range(20):
    try:
        print(f'  attempt {attempt+1}: writing {len(alive_rows):,} rows...', flush=True)
        with open(tmp, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=header, lineterminator='\n', quoting=csv.QUOTE_MINIMAL, extrasaction='ignore')
            w.writeheader()
            for i in range(0, len(alive_rows), chunk_size):
                w.writerows(alive_rows[i:i+chunk_size])
                if i % 50000 == 0 and i > 0:
                    print(f'    wrote {i:,}/{len(alive_rows):,}', flush=True)
        print(f'  file written, replacing...', flush=True)
        os.replace(tmp, CSV_PATH)
        print(f'  Saved {len(alive_rows):,} rows to {CSV_PATH}', flush=True)
        break
    except PermissionError as e:
        if attempt % 10 == 0:
            print(f'  retry {attempt}: {e}', flush=True)
        time.sleep(2 + random.uniform(0, 3))
    except Exception as e:
        print(f'  err: {e}', flush=True)
        time.sleep(2)
else:
    print('ERROR: Could not save after 20 retries', flush=True)
