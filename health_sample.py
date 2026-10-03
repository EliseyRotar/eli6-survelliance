import csv
import random

with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv', 'r', encoding='utf-8', newline='') as f:
    rows = list(csv.reader(f))
print(f'total: {len(rows)-1}')

# Sample diverse sources
random.seed(42)
samples = []
sources_seen = {}
# Try to get a diverse sample - 5 per source
random.shuffle(rows[1:])
for r in rows:
    if len(r) > 33:
        src = r[33].split('source=')[1].split(',')[0].split(';')[0] if 'source=' in r[33] else '?'
        if sources_seen.get(src, 0) < 5:
            samples.append(r)
            sources_seen[src] = sources_seen.get(src, 0) + 1
        if sum(sources_seen.values()) >= 30:
            break

# Print sample (avoid UnicodeEncodeError by encoding output)
print(f'Sample of {len(samples)} cams from {len(sources_seen)} sources:')
for r in samples:
    name = r[1][:30].encode('ascii', 'replace').decode('ascii')
    host = r[31][:25].encode('ascii', 'replace').decode('ascii')
    url = r[3][:60].encode('ascii', 'replace').decode('ascii')
    print(f'  [{r[0]}] {name:<30} | {host:<25} | {url}')
