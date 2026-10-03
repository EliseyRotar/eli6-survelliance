"""Kill all HLS proxies."""
import psutil
import time

killed = []
for p in psutil.process_iter(['name', 'cmdline', 'pid']):
    try:
        cmd = ' '.join(p.info['cmdline'] or [])
        if 'hls_proxy' in cmd:
            p.kill()
            killed.append(p.info['pid'])
    except:
        pass
time.sleep(3)

# Verify all gone
for p in psutil.process_iter(['name', 'cmdline', 'pid']):
    try:
        cmd = ' '.join(p.info['cmdline'] or [])
        if 'hls_proxy' in cmd:
            print('Still alive:', p.info['pid'])
    except:
        pass
print(f'Killed: {killed}')
