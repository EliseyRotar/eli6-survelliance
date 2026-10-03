"""Final cleanup - kill extras, start needed."""
import psutil
import time
import subprocess
import os

# Kill all but 1 of each
keep = {
    'fl511_browser_fallback.py': 1,
    'bf_runner.py': 1,
}

# Get all matching procs
procs_by_script = {}
for p in psutil.process_iter(['name', 'cmdline', 'pid', 'create_time']):
    try:
        cmd = ' '.join(p.info['cmdline'] or [])
        if 'python' in (p.info['name'] or '').lower():
            for script in keep:
                if script in cmd:
                    if script not in procs_by_script:
                        procs_by_script[script] = []
                    procs_by_script[script].append((p.info['create_time'], p.info['pid']))
                    break
    except:
        pass

# Kill extras
killed = []
for script, keep_count in keep.items():
    procs = procs_by_script.get(script, [])
    procs.sort()  # Oldest first
    to_kill = procs[:-keep_count]
    for _, pid in to_kill:
        try:
            psutil.Process(pid).kill()
            killed.append((script, pid))
        except:
            pass
time.sleep(2)

for s, p in killed:
    print(f'  killed {s} pid={p}')

# Start needed
needed = [
    'fl511_full_live_direct_v2.py',
    'rtsp_bf_v2.py',
]

for script in needed:
    path = rf'C:\Users\eli6-admin\Documents\eli6-surveillance\{script}'
    if os.path.exists(path):
        try:
            DETACHED_PROCESS = 0x00000008
            subprocess.Popen(
                ['C:\\Users\\eli6-admin\\AppData\\Local\\Programs\\Python\\Python312\\python.exe', path],
                creationflags=DETACHED_PROCESS,
                cwd=os.path.dirname(path),
            )
            print(f'  started {script}')
            time.sleep(2)
        except Exception as e:
            print(f'  err {script}: {e}')
print('Done')
