"""Check video upgrade progress."""
import json
import os
p = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\video_upgrade_progress.json'
if os.path.exists(p):
    with open(p) as f:
        d = json.load(f)
    tested = d.get('tested', {})
    upgraded = d.get('upgraded', 0)
    print(f'Tested hosts: {len(tested)}')
    print(f'Upgraded: {upgraded}')
else:
    print('Progress file does not exist yet')
