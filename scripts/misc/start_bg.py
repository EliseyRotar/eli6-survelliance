"""Start all bg processes (excluding reaper which is already running)."""
import subprocess
import os
import time

procs = [
    ('fl511_full_live_direct_v2.py', r'C:\Users\eli6-admin\Documents\eli6-surveillance\scripts/fl511\fl511_full_live_direct_v2.py'),
    ('fl511_browser_fallback.py', r'C:\Users\eli6-admin\Documents\eli6-surveillance\scripts/fl511\fl511_browser_fallback.py'),
    ('bf_runner.py', r'C:\Users\eli6-admin\Documents\eli6-surveillance\scripts/brute\bf_runner.py'),
    ('rtsp_bf_v2.py', r'C:\Users\eli6-admin\Documents\eli6-surveillance\scripts/brute\rtsp_bf_v2.py'),
    ('insecam_private_scanner.py', r'C:\Users\eli6-admin\Documents\eli6-surveillance\scripts/brute\insecam_private_scanner.py'),
    ('private_cams_discovery.py', r'C:\Users\eli6-admin\Documents\eli6-surveillance\scripts/brute\private_cams_discovery.py'),
    ('insecam_country_v2.py', r'C:\Users\eli6-admin\Documents\eli6-surveillance\scripts/scan\insecam_country_v2.py'),
]

for name, path in procs:
    if not os.path.exists(path):
        # Try the other dir
        alt = path.replace('surveillance', 'survelliance')
        if os.path.exists(alt):
            path = alt
        else:
            print(f'  {name}: NOT FOUND at {path}')
            continue
    try:
        DETACHED_PROCESS = 0x00000008
        subprocess.Popen(
            ['C:\\Users\\eli6-admin\\AppData\\Local\\Programs\\Python\\Python312\\python.exe', path],
            creationflags=DETACHED_PROCESS,
            cwd=os.path.dirname(path),
        )
        print(f'  started {name}')
        time.sleep(1)
    except Exception as e:
        print(f'  err {name}: {e}')
print('Done')
