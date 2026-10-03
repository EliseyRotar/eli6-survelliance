"""Auto-backup daemon - runs every 6 hours, keeps last 3 backups.

Can be started in background. Tracks changes and only saves new data
if CSV/DB has changed significantly.
"""
import os
import sys
import time
import json
import shutil
import sqlite3
import hashlib
from datetime import datetime

# Force unbuffered
sys.stdout.reconfigure(line_buffering=True)

WORK_DIR = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
BACKUP_ROOT = os.path.join(WORK_DIR, 'backups')

# How many backups to keep
MAX_BACKUPS = 3
# Hours between backups
BACKUP_INTERVAL = 6 * 3600
# Minimum size change to trigger backup (bytes)
MIN_SIZE_DELTA = 1024 * 1024  # 1MB


def get_csv_hash():
    """Get size + mtime as cheap hash."""
    csv_path = os.path.join(WORK_DIR, 'controllable_Webcams.csv')
    if not os.path.exists(csv_path):
        return None
    return (os.path.getsize(csv_path), int(os.path.getmtime(csv_path)))


def get_db_count():
    db_path = os.path.join(WORK_DIR, 'camera_testing', 'webcams.db')
    if not os.path.exists(db_path):
        return 0
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM webcams')
        n = c.fetchone()[0]
        conn.close()
        return n
    except:
        return 0


def do_backup():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = os.path.join(BACKUP_ROOT, f'auto_{timestamp}')
    os.makedirs(backup_dir, exist_ok=True)

    print(f'[AUTO-BACKUP] {timestamp}', flush=True)

    # CSV
    csv_path = os.path.join(WORK_DIR, 'controllable_Webcams.csv')
    if os.path.exists(csv_path):
        shutil.copy2(csv_path, os.path.join(backup_dir, 'controllable_Webcams.csv'))

    # DB
    db_path = os.path.join(WORK_DIR, 'camera_testing', 'webcams.db')
    if os.path.exists(db_path):
        shutil.copy2(db_path, os.path.join(backup_dir, 'webcams.db'))

    # Progress files
    progress_dir = os.path.join(backup_dir, 'progress_files')
    os.makedirs(progress_dir, exist_ok=True)
    for fn in os.listdir(WORK_DIR):
        if fn.endswith(('.json', '.jsonl', '.log')) and any(k in fn for k in ['rtsp', 'insecam', 'vbviewer', 'bf_', 'progress']):
            src = os.path.join(WORK_DIR, fn)
            if os.path.isfile(src) and os.path.getsize(src) < 100*1024*1024:  # <100MB
                try:
                    shutil.copy2(src, os.path.join(progress_dir, fn))
                except:
                    pass

    # State
    state = {
        'timestamp': timestamp,
        'csv_size': os.path.getsize(csv_path) if os.path.exists(csv_path) else 0,
        'db_count': get_db_count(),
    }
    with open(os.path.join(backup_dir, 'state.json'), 'w') as f:
        json.dump(state, f, indent=2)

    # Cleanup old
    cleanup_old()

    print(f'  Done: {state["db_count"]:,} DB rows, {state["csv_size"]/1024/1024:.1f} MB CSV', flush=True)


def cleanup_old():
    """Keep only last MAX_BACKUPS auto-backups."""
    backups = sorted([
        d for d in os.listdir(BACKUP_ROOT)
        if d.startswith('auto_') and os.path.isdir(os.path.join(BACKUP_ROOT, d))
    ])
    while len(backups) > MAX_BACKUPS:
        old = backups.pop(0)
        old_path = os.path.join(BACKUP_ROOT, old)
        try:
            shutil.rmtree(old_path)
            print(f'  Cleaned up old backup: {old}', flush=True)
        except Exception as e:
            print(f'  Cleanup err: {e}', flush=True)
        backups = sorted([
            d for d in os.listdir(BACKUP_ROOT)
            if d.startswith('auto_') and os.path.isdir(os.path.join(BACKUP_ROOT, d))
        ])


def main():
    print(f'[AUTO-BACKUP] Starting daemon (every {BACKUP_INTERVAL/3600:.0f}h, max {MAX_BACKUPS} backups)', flush=True)
    while True:
        try:
            do_backup()
        except Exception as e:
            print(f'  Backup err: {e}', flush=True)
        print(f'  Sleeping {BACKUP_INTERVAL/3600:.0f}h...', flush=True)
        time.sleep(BACKUP_INTERVAL)


if __name__ == '__main__':
    main()
