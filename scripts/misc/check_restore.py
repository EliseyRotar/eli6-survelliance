"""CSV crash detection and auto-restore.

Checks if CSV is corrupted (size=0, missing header, too few rows, contains null bytes).
If corrupted, restores from webcams.db (SQLite backup) first, then from latest backup.

Run on PC startup or as a watchdog.
"""
import os
import sys
import time
import csv
import sqlite3
import shutil
from datetime import datetime

# Force unbuffered
sys.stdout.reconfigure(line_buffering=True)

WORK_DIR = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
CSV_PATH = os.path.join(WORK_DIR, 'controllable_Webcams.csv')
DB_PATH = os.path.join(WORK_DIR, 'camera_testing', 'webcams.db')
BACKUP_LATEST = os.path.join(WORK_DIR, 'backups', 'latest', 'controllable_Webcams.csv')


def check_csv_health():
    """Check if CSV is healthy. Returns (status, message, row_count)."""
    if not os.path.exists(CSV_PATH):
        return ('missing', 'CSV file does not exist', 0)
    size = os.path.getsize(CSV_PATH)
    if size < 10000:  # Less than 10KB = suspicious
        return ('corrupt', f'CSV too small ({size} bytes)', 0)
    # Check for null bytes
    try:
        with open(CSV_PATH, 'rb') as f:
            data = f.read(1_000_000)
            if b'\x00' in data:
                return ('corrupt', 'CSV contains null bytes', 0)
    except Exception as e:
        return ('corrupt', f'Cannot read: {e}', 0)
    # Check header
    try:
        with open(CSV_PATH, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.reader(f)
            header = next(reader)
            if len(header) < 30:
                return ('corrupt', f'Header has only {len(header)} columns (expected 35)', 0)
            # Count rows (estimate)
            f.seek(0)
            n = sum(1 for _ in f) - 1
        return ('healthy', 'OK', n)
    except Exception as e:
        return ('corrupt', str(e)[:100], 0)


def restore_from_db():
    """Restore CSV from SQLite database."""
    if not os.path.exists(DB_PATH):
        return False
    print(f'[RESTORE] Trying to restore from webcams.db...', flush=True)
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in c.fetchall()]
        if 'webcams' not in tables:
            print(f'  No webcams table in DB. Tables: {tables}', flush=True)
            conn.close()
            return False
        c.execute('SELECT COUNT(*) FROM webcams')
        n = c.fetchone()[0]
        print(f'  DB has {n:,} rows', flush=True)
        if n < 100000:
            print(f'  Too few rows, skipping', flush=True)
            conn.close()
            return False
        c.execute('SELECT * FROM webcams LIMIT 1')
        cols_db = [d[0] for d in c.description]
        c.execute('SELECT * FROM webcams')
        rows = c.fetchall()
        conn.close()

        # Backup bad CSV
        if os.path.exists(CSV_PATH):
            shutil.copy2(CSV_PATH, CSV_PATH + '.bad')

        # Write new CSV
        print(f'  Writing {len(rows):,} rows to CSV...', flush=True)
        with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
            w.writerow(cols_db)
            w.writerows(rows)
        print(f'  Done!', flush=True)
        return True
    except Exception as e:
        print(f'  DB restore err: {e}', flush=True)
        return False


def restore_from_backup():
    """Restore CSV from latest backup."""
    if not os.path.exists(BACKUP_LATEST):
        return False
    size = os.path.getsize(BACKUP_LATEST) / 1024 / 1024
    print(f'[RESTORE] Trying to restore from latest backup ({size:.1f} MB)...', flush=True)
    if size < 50:  # Less than 50MB = suspicious
        return False
    try:
        if os.path.exists(CSV_PATH):
            shutil.copy2(CSV_PATH, CSV_PATH + '.bad')
        shutil.copy2(BACKUP_LATEST, CSV_PATH)
        print(f'  Restored from backup', flush=True)
        return True
    except Exception as e:
        print(f'  Backup restore err: {e}', flush=True)
        return False


def main():
    print(f'[CHECK] {datetime.now().isoformat()}', flush=True)
    status, msg, n = check_csv_health()
    print(f'  Status: {status} - {msg}', flush=True)
    print(f'  Rows: {n:,}', flush=True)
    if status == 'healthy':
        print(f'  CSV is healthy, no action needed', flush=True)
        return
    # Try DB first
    if restore_from_db():
        # Verify
        status, msg, n = check_csv_health()
        print(f'  After DB restore: {status} - {msg} - {n:,} rows', flush=True)
        return
    # Then backup
    if restore_from_backup():
        status, msg, n = check_csv_health()
        print(f'  After backup restore: {status} - {msg} - {n:,} rows', flush=True)
        return
    print(f'  FATAL: Could not restore CSV!', flush=True)


if __name__ == '__main__':
    main()
