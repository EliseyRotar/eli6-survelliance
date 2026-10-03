import json
p = r'C:\Users\eli6-admin\Documents\eli6-surveillance\rtsp_bf.json'
with open(p) as f:
    d = json.load(f)
n_total = len(d)
n_unlocked = sum(1 for v in d.values() if isinstance(v, dict) and v.get('unlocked'))
print('Entries:', n_total, 'Unlocked:', n_unlocked)
count = 0
for k, v in d.items():
    if isinstance(v, dict) and v.get('unlocked'):
        count += 1
        if count <= 5:
            print('  ', k, ':', v.get('found'))
