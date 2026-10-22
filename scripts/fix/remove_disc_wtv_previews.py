"""Remove argus disc_* feratel preview-thumbnail rows from the CSV.

These 1,728 rows carry wtvthmb/wtvpict JPEG live URLs (static previews
with a baked-in play button, dcsdesign=WTP_*/design=v5). They duplicate
feratel cams already ingested as ft_ rows with real rolling-fragment
video via the /api/feratel/* broker. The user explicitly asked for them
to be removed.
"""
import csv
import os
import random
import sys
import time

sys.stdout.reconfigure(line_buffering=True)

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'

csv.field_size_limit(2**31 - 1)
print(f'Loading {CSV_PATH}...', flush=True)
with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    header = reader.fieldnames
print(f'  {len(rows):,} rows', flush=True)


def is_disc_preview(row):
    cid = row.get('csv_id') or ''
    if not cid.startswith('disc_'):
        return False
    lv = row.get('live_stream_url') or ''
    return 'wtvthmb.feratel' in lv or 'wtvpict.feratel' in lv


kept = []
removed = []
for row in rows:
    if is_disc_preview(row):
        removed.append(row)
    else:
        kept.append(row)

print(f'  disc_* wtvthmb/wtvpict preview rows to remove: {len(removed):,}', flush=True)
print(f'  rows to keep: {len(kept):,}', flush=True)

if not removed:
    print('Nothing to remove', flush=True)
    sys.exit(0)

tmp = CSV_PATH + '.tmp'
chunk_size = 10000
for attempt in range(20):
    try:
        print(f'  attempt {attempt + 1}: writing {len(kept):,} rows...', flush=True)
        with open(tmp, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=header, lineterminator='\n',
                                quoting=csv.QUOTE_MINIMAL, extrasaction='ignore')
            w.writeheader()
            for i in range(0, len(kept), chunk_size):
                w.writerows(kept[i:i + chunk_size])
                if i % 50000 == 0 and i > 0:
                    print(f'    wrote {i:,}/{len(kept):,}', flush=True)
        print('  file written, replacing...', flush=True)
        os.replace(tmp, CSV_PATH)
        print(f'  Saved {len(kept):,} rows to {CSV_PATH}', flush=True)
        break
    except PermissionError as e:
        if attempt % 10 == 0:
            print(f'  retry {attempt}: {e}', flush=True)
        time.sleep(2 + random.uniform(0, 3))
    except Exception as e:
        print(f'  err: {e}', flush=True)
        time.sleep(2)
else:
    print('FAILED to write CSV after 20 attempts', flush=True)
    sys.exit(1)

# Sample of removed idxs for the log
print('  sample removed idxs:', [r['idx'] for r in removed[:8]], flush=True)
