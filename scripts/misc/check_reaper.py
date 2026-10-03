"""Check reaper state."""
import json
import os
p = r'C:\Users\eli6-admin\Documents\eli6-surveillance\reap_results.json'
if os.path.exists(p):
    with open(p) as f:
        d = json.load(f)
    print(f'Reaper: {len(d):,} cams probed')
else:
    print('No reaper data')
