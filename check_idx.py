import csv
csv.field_size_limit(2**31-1)
# Check idx 257 again
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv', encoding='utf-8', errors='replace') as f:
    r = csv.DictReader(f)
    for row in r:
        if row.get('idx') == '257':
            print('idx 257:', 'url=', (row.get('url') or '')[:60], 'live=', repr(row.get('live_status')))
            break
