import csv
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv', 'r', encoding='utf-8', newline='') as f:
    rows = list(csv.reader(f))
header = rows[0]

# Look at argus-v2 entries to confirm lat/lon are real
argus_v2 = [r for r in rows[1:] if len(r) > 31 and 'source=argus-v2' in r[31]]
print(f'argus-v2 total: {len(argus_v2)}')
print()
print('Sample of argus-v2 lat/lon:')
for r in argus_v2[:5]:
    idx, name, url, lsu = r[0], r[1], r[2], r[3]
    country, region, city, lat, lon = r[19], r[20], r[21], r[23], r[24]
    print(f'  idx={idx} lat={lat!r} lon={lon!r} country={country!r} city={city!r}')
    print(f'    name={name[:60]}')
print()
# Now check if lat/lon are sane
import math
real_latlon = 0
fake_latlon = 0
weird = []
for r in argus_v2:
    if len(r) <= 24:
        continue
    try:
        lat = float(r[23]); lon = float(r[24])
        if -90 <= lat <= 90 and -180 <= lon <= 180 and (lat != 0 or lon != 0):
            real_latlon += 1
        else:
            fake_latlon += 1
            weird.append((r[0], lat, lon, r[1][:40]))
    except (ValueError, TypeError):
        fake_latlon += 1
print(f'argus-v2 real lat/lon: {real_latlon}/{len(argus_v2)}')
print(f'argus-v2 missing/zero: {fake_latlon}')
if weird[:5]:
    print('  weird samples:')
    for w in weird[:5]:
        print(f'    {w}')
