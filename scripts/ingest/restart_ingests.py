"""Restart ingest scripts after CSV cleanup."""
import subprocess
import os
import time

scripts = [
    'camera_testing/trafficvision_full_ingest_v3.py',
    'camera_testing/opencctv_ingest.py',
    'camera_testing/tfl_ingest.py',
    'camera_testing/netlas_ingest.py',
    'camera_testing/caltrans_ingest.py',
    'camera_testing/argus_ingest_v3.py',
    'cam_reaper.py',
]

WORK = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
PYTHON = r'C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\python.exe'

for s in scripts:
    path = os.path.join(WORK, s)
    if os.path.exists(path):
        try:
            DETACHED_PROCESS = 0x00000008
            subprocess.Popen(
                [PYTHON, path],
                creationflags=DETACHED_PROCESS,
                cwd=os.path.dirname(path),
            )
            print('started', s)
            time.sleep(2)
        except Exception as e:
            print('err', s, e)
    else:
        print('NOT FOUND:', path)
