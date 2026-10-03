"""Kill duplicate bg processes, keep 1 of each."""
import psutil
import time
import os

# Define what's a duplicate
duplicate_sets = {
    'fl511_browser_fallback.py': 2,  # Keep 2
    'bf_runner.py': 1,
    'fl511_simple_direct.py': 0,  # Kill all
    'fl511_full_live.py': 0,
    'fl511_full_live_direct.py': 0,
    'fl511_full_live_v2.py': 0,
    'fl511_full_live_direct_v2.py': 1,  # Keep this one
}

# Get all matching procs sorted by uptime (oldest first)
procs_by_script = {}
for p in psutil.process_iter(['name', 'cmdline', 'pid', 'create_time']):
    try:
        cmd = ' '.join(p.info['cmdline'] or [])
        if 'python' in (p.info['name'] or '').lower():
            for script in duplicate_sets:
                if script in cmd:
                    if script not in procs_by_script:
                        procs_by_script[script] = []
                    procs_by_script[script].append((p.info['create_time'], p.info['pid']))
                    break
    except:
        pass

killed = []
for script, keep_count in duplicate_sets.items():
    procs = procs_by_script.get(script, [])
    procs.sort()  # Oldest first
    to_kill = procs[:-keep_count] if keep_count > 0 else procs
    for _, pid in to_kill:
        try:
            psutil.Process(pid).kill()
            killed.append((script, pid))
        except:
            pass

time.sleep(2)
for s, p in killed:
    print(f'  killed {s} pid={p}')
print(f'Total killed: {len(killed)}')
