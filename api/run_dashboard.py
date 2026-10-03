# eli6-dashboard — background launcher
# Keeps the Flask API running, restarts if killed.
import subprocess, time, sys, os
from pathlib import Path

DASH_DIR = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance')
API_SCRIPT = DASH_DIR / 'api' / 'app.py'
PY = r'C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\python.exe'
LOG = Path(r'C:\Users\eli6-admin\AppData\Local\Temp\eli6-dashboard.log')
PID_FILE = DASH_DIR / 'eli6-dashboard.pid'

def is_running():
    if not PID_FILE.exists(): return False
    try:
        pid = int(PID_FILE.read_text().strip())
        import subprocess
        out = subprocess.run(['tasklist', '/FI', f'PID eq {pid}'], capture_output=True, text=True, timeout=2)
        return str(pid) in out.stdout
    except: return False

if __name__ == '__main__':
    if is_running():
        print('already running')
        sys.exit(0)
    PID_FILE.write_text(str(os.getpid()))
    print(f'PID {os.getpid()} started')
    while True:
        try:
            with open(LOG, 'a') as logf:
                subprocess.run([PY, str(API_SCRIPT), '8773'],
                             cwd=str(DASH_DIR),
                             stdout=logf, stderr=logf, check=True)
        except subprocess.CalledProcessError as e:
            print(f'crashed: {e}', file=sys.stderr)
        except KeyboardInterrupt:
            PID_FILE.unlink(missing_ok=True)
            break
        time.sleep(3)
        if not is_running():
            print('restarting...')