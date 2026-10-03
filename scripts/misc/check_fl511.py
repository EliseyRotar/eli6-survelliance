"""Check fl511 cams in our CSV."""
import csv
import re
from collections import Counter

csv.field_size_limit(2**31 - 1)
fl_count = 0
fl_samples = []

with open('controllable_Webcams.csv', 'r', encoding='utf-8', errors='replace') as f:
    for row in csv.DictReader(f):
        url = row.get('url', '') or ''
        notes = row.get('notes', '') or ''
        host = row.get('host', '') or ''
        # Check fl511 specifically
        if 'fl511' in url.lower() or 'fl511' in host.lower() or 'fl511' in notes.lower():
            fl_count += 1
            if len(fl_samples) < 20:
                fl_samples.append({
                    'url': url,
                    'host': host,
                    'notes': notes[:200],
                    'live_status': row.get('live_status', ''),
                    'type': row.get('type', ''),
                })

print(f'fl511 cams: {fl_count}')
print()
for s in fl_samples:
    print(f'  URL: {s["url"]}')
    print(f'  host: {s["host"]}')
    print(f'  type: {s["type"]} status: {s["live_status"]}')
    print(f'  notes: {s["notes"]}')
    print()
