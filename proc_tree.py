import psutil
import time
procs = []
for p in psutil.process_iter(['name', 'cmdline', 'pid', 'create_time']):
    try:
        cmd = ' '.join(p.info['cmdline'] or [])
        if 'python' in (p.info['name'] or '').lower() and 'eli6' in cmd.lower():
            uptime = time.time() - p.info['create_time']
            parts = cmd.split()
            script = ''
            for part in parts:
                if '.py' in part and 'python' not in part:
                    script = part.split('\\')[-1]
                    break
            procs.append((uptime, p.pid, script))
    except:
        pass
procs.sort()
for u, pid, s in procs:
    print('  uptime=%ds pid=%d script=%s' % (u, pid, s))
