"""Check fl511 progress."""
import json
import os
import time

p = r'C:\Users\eli6-admin\Documents\eli6-surveillance\fl511_cams_all.json'
mtime = os.path.getmtime(p)
print(f'fl511_cams_all.json mtime: {time.ctime(mtime)} ({time.time()-mtime:.0f}s ago)')
with open(p) as f:
    d = json.load(f)
print(f'Cams: {len(d.get("cams", [])):,}')
