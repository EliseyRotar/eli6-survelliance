import csv
csv.field_size_limit(2**31-1)
n_bf = 0
n_with_user = 0
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv', encoding='utf-8', errors='replace') as f:
    r = csv.DictReader(f)
    for row in r:
        notes = row.get('notes') or ''
        if 'BF_unlocked' in notes:
            n_bf += 1
        if row.get('auth_user'):
            n_with_user += 1
print(f'Rows with BF_unlocked note: {n_bf:,}')
print(f'Rows with auth_user: {n_with_user:,}')
# Sample
n = 0
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv', encoding='utf-8', errors='replace') as f:
    r = csv.DictReader(f)
    for row in r:
        if 'BF_unlocked' in (row.get('notes') or ''):
            n += 1
            if n <= 3:
                auth = row.get('auth_user') or ''
                pwd = row.get('auth_pass') or ''
                notes = (row.get('notes') or '')[:100]
                print('  auth=' + auth + '/' + pwd + ' notes=' + notes)
