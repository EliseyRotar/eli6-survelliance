"""Kill all reaper processes by PID."""
import psutil
import os

pids_to_kill = [11424, 11716, 22388, 23972, 28388, 32572, 33516, 34400]
for pid in pids_to_kill:
    try:
        p = psutil.Process(pid)
        cmd = ' '.join(p.cmdline() or [])
        if 'cam_reaper' in cmd:
            p.kill()
            print(f'  killed pid={pid}')
    except psutil.NoSuchProcess:
        pass
    except Exception as e:
        print(f'  err pid={pid}: {e}')
print('Done')
