"""Watchdog - periodically checks CSV health and auto-restores.

Runs in background, checks every 5 minutes. If CSV is corrupt, runs check_restore.
"""
import os
import sys
import time
import subprocess
from datetime import datetime

sys.stdout.reconfigure(line_buffering=True)

WORK_DIR = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
INTERVAL = 300  # 5 minutes


def main():
    print(f'[WATCHDOG] Starting CSV health watchdog (every {INTERVAL}s)', flush=True)
    while True:
        try:
            t0 = datetime.now().isoformat()
            result = subprocess.run(
                ['python', '-u', 'check_restore.py'],
                cwd=WORK_DIR,
                capture_output=True, text=True, timeout=600
            )
            output = result.stdout + result.stderr
            if 'CORRUPT' in output.upper() or 'RESTORE' in output.upper() or 'FATAL' in output.upper():
                print(f'\n[{t0}] CHECK FOUND ISSUES:', flush=True)
                print(output, flush=True)
            else:
                print(f'[{t0}] OK ({len(output)} bytes output)', flush=True)
        except Exception as e:
            print(f'[{datetime.now().isoformat()}] Watchdog err: {e}', flush=True)
        time.sleep(INTERVAL)


if __name__ == '__main__':
    main()
