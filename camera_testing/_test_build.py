import sys
sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')
from trafficvision_full_ingest_v3 import build_row, get_header
header = get_header()
print('header len:', len(header))
rec = {
    'id': 'test-1', 'videoUrl': 'http://example.com/stream.m3u8',
    'lat': 12.34, 'lng': -45.67,
    'city': 'Test City', 'state': 'Test State',
}
result = build_row(rec, 'test', header)
if result:
    row, full_id, url = result
    print('row keys:', sorted(row.keys()))
    print('full_id:', full_id)
    print('url:', url)
    for h in header:
        v = row.get(h, 'MISSING')
        print(f'  {h}: {v}')
else:
    print('build_row returned None')
