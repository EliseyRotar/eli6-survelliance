import csv
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv', 'r', encoding='utf-8', newline='') as f:
    rows = list(csv.reader(f))

m3u8 = [r for r in rows[1:] if len(r) > 3 and r[3] and '.m3u8' in r[3].lower()]
print(f"m3u8 total: {len(m3u8)}")
print('m3u8 sample:')
for r in m3u8[:15]:
    print(f"  idx={r[0]:<8} {r[1][:35]:<35} {r[3][:70]}")

windy = [r for r in rows[1:] if len(r) > 3 and r[3] and 'windy' in r[3].lower()]
print(f"\nWindy total: {len(windy)}")
print('Windy sample:')
for r in windy[:5]:
    print(f"  idx={r[0]:<8} {r[1][:35]:<35} {r[3][:70]}")

# breakdown by source tag
sources = {}
for r in rows[1:]:
    if len(r) <= 31:
        continue
    notes = r[31]
    if 'source=' in notes:
        src = notes.split('source=')[1].split(',')[0].split(';')[0]
    else:
        src = '?'
    sources[src] = sources.get(src, 0) + 1
print('\nSources:')
for s, c in sorted(sources.items(), key=lambda x: -x[1])[:20]:
    print(f'  {s}: {c}')
