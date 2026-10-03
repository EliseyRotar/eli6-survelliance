import csv
import re
csv.field_size_limit(2**31-1)
n = 0
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv', encoding='utf-8', errors='replace') as f:
    r = csv.DictReader(f)
    for row in r:
        notes = row.get('notes') or ''
        if 'BF' in notes or 'unlocked' in notes.lower():
            n += 1
            if n <= 5:
                print('  notes:', notes[:200].encode('utf-8', errors='replace').decode('utf-8'))
print(f'Total with BF/unlocked in notes: {n}')
