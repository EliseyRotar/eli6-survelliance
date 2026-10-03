"""Kill the reaper process."""
import psutil
import os
import time

# Find reaper procs
for p in psutil.process_iter(['name', 'cmdline', 'pid']):
    try:
        cmd = ' '.join(p.info['cmdline'] or [])
        if 'cam_reaper' in cmd and 'psutil' not in cmd and 'kill' not in cmd:
            print('Killing pid=' + str(p.pid))
            p.kill()
            time.sleep(2)
    except:
        pass

# Remove stale PID file
pid_file = r'C:\Users\eli6-admin\Documents\eli6-surveillance\cam_reaper.pid'
if os.path.exists(pid_file):
    try:
        os.remove(pid_file)
        print('Removed PID file')
    except:
        pass

print('Done')
