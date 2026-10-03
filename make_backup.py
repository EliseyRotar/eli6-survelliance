"""Comprehensive backup of all critical files.

Creates:
- backups/backup_<timestamp>/controllable_Webcams.csv (current)
- backups/backup_<timestamp>/webcams.db (full SQLite)
- backups/backup_<timestamp>/progress_files/ (all progress JSON files)
- backups/backup_<timestamp>/state_snapshot.json (metadata)

Also copies latest to backups/latest/ for quick access.
"""
import os
import sys
import json
import shutil
import time
import csv
import glob
import sqlite3
from datetime import datetime

# Force unbuffered
sys.stdout.reconfigure(line_buffering=True)

WORK_DIR = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
BACKUP_ROOT = os.path.join(WORK_DIR, 'backups')


def main():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = os.path.join(BACKUP_ROOT, f'backup_{timestamp}')
    os.makedirs(backup_dir, exist_ok=True)

    print(f'[BACKUP] Creating backup at {backup_dir}', flush=True)

    # 1. CSV
    csv_path = os.path.join(WORK_DIR, 'controllable_Webcams.csv')
    if os.path.exists(csv_path):
        size = os.path.getsize(csv_path) / 1024 / 1024
        print(f'  Backing up CSV ({size:.1f} MB)...', flush=True)
        # Use chunked copy to handle large files
        with open(csv_path, 'rb') as f_in:
            with open(os.path.join(backup_dir, 'controllable_Webcams.csv'), 'wb') as f_out:
                while True:
                    chunk = f_in.read(64 * 1024)
                    if not chunk:
                        break
                    f_out.write(chunk)
        print(f'  CSV backup done', flush=True)

    # 2. SQLite DB
    db_path = os.path.join(WORK_DIR, 'camera_testing', 'webcams.db')
    if os.path.exists(db_path):
        size = os.path.getsize(db_path) / 1024 / 1024
        print(f'  Backing up webcams.db ({size:.1f} MB)...', flush=True)
        shutil.copy2(db_path, os.path.join(backup_dir, 'webcams.db'))
        # Also save row count
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM webcams')
            n = c.fetchone()[0]
            conn.close()
            with open(os.path.join(backup_dir, 'webcams_count.txt'), 'w') as f:
                f.write(f'{n}\n')
            print(f'    DB has {n:,} rows', flush=True)
        except Exception as e:
            print(f'    DB count err: {e}', flush=True)

    # 3. Progress files
    progress_dir = os.path.join(backup_dir, 'progress_files')
    os.makedirs(progress_dir, exist_ok=True)
    progress_files = [
        'rtsp_proxy_streams.json',
        'rtsp_full_results.json',
        'rtsp_full_results_v2.json',
        'rtsp_endpoints.jsonl',
        'rtsp_bf_v2_progress.json',
        'hikvision_rtsp_bf_progress.json',
        'vbviewer_native_bf_progress.json',
        'vbviewer_bf_cve_progress.json',
        'insecam_country_results.json',
        'insecam_simple_progress.json',
        'insecam_loop.log',
        'rtsp_proxy_v2.log',
        'rtsp_proxy_v2.err',
    ]
    n_prog = 0
    for fn in progress_files:
        src = os.path.join(WORK_DIR, fn)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(progress_dir, fn))
            n_prog += 1
    print(f'  Backed up {n_prog} progress files', flush=True)

    # 4. tv_catalog_full.json and shards (TrafficVision)
    tv_files = [
        'tv_catalog_full.json',
        'tv_shards',
    ]
    for fn in tv_files:
        src = os.path.join(WORK_DIR, 'camera_testing', fn)
        if os.path.exists(src):
            dst = os.path.join(backup_dir, 'tv_' + fn.replace('/', '_'))
            if os.path.isdir(src):
                shutil.copytree(src, dst)
                print(f'  Backed up TV {fn} (dir)', flush=True)
            else:
                shutil.copy2(src, dst)
                size = os.path.getsize(src) / 1024 / 1024
                print(f'  Backed up TV {fn} ({size:.1f} MB)', flush=True)

    # 5. State snapshot
    state = {
        'timestamp': timestamp,
        'csv_path': csv_path,
        'csv_size_bytes': os.path.getsize(csv_path) if os.path.exists(csv_path) else 0,
        'csv_mtime': os.path.getmtime(csv_path) if os.path.exists(csv_path) else 0,
    }
    # Get row count
    try:
        with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
            n = sum(1 for _ in f) - 1
        state['csv_rows'] = n
    except:
        state['csv_rows'] = 0
    # Get DB count
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM webcams')
        state['db_rows'] = c.fetchone()[0]
        conn.close()
    except:
        state['db_rows'] = 0

    with open(os.path.join(backup_dir, 'state_snapshot.json'), 'w') as f:
        json.dump(state, f, indent=2)
    print(f'  State snapshot saved', flush=True)

    # 6. Create "latest" symlink-equivalent
    latest = os.path.join(BACKUP_ROOT, 'latest')
    if os.path.exists(latest):
        try:
            if os.path.isdir(latest):
                shutil.rmtree(latest)
            else:
                os.remove(latest)
        except:
            pass
    # Use junction on Windows
    try:
        os.system(f'mklink /J "{latest}" "{backup_dir}"')
    except:
        # Fallback: copy small files
        try:
            shutil.copytree(backup_dir, latest)
        except Exception as e:
            print(f'  latest link err: {e}', flush=True)
    print(f'  latest -> {backup_dir}', flush=True)

    # Print summary
    print(f'\n[BACKUP] Summary:', flush=True)
    print(f'  Timestamp: {timestamp}', flush=True)
    print(f'  CSV rows: {state["csv_rows"]:,}', flush=True)
    print(f'  CSV size: {state["csv_size_bytes"]/1024/1024:.1f} MB', flush=True)
    print(f'  DB rows: {state["db_rows"]:,}', flush=True)
    print(f'  Backup dir: {backup_dir}', flush=True)

    # List all backups
    print(f'\n[ALL BACKUPS]:', flush=True)
    for d in sorted(os.listdir(BACKUP_ROOT)):
        full = os.path.join(BACKUP_ROOT, d)
        if os.path.isdir(full):
            size = sum(os.path.getsize(os.path.join(root, f)) for root, _, files in os.walk(full) for f in files) / 1024 / 1024
            print(f'  {d}: {size:.1f} MB', flush=True)


if __name__ == '__main__':
    main()
