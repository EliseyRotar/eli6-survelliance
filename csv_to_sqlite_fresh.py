"""Convert current CSV to SQLite - quick safety measure.

Reads master CSV, writes to webcams.db with same schema.
"""
import os
import sys
import csv
import sqlite3
import time

sys.stdout.reconfigure(line_buffering=True)

WORK_DIR = r'C:\Users\eli6-admin\Documents\eli6-surveillance'
CSV_PATH = os.path.join(WORK_DIR, 'controllable_Webcams.csv')
DB_PATH = os.path.join(WORK_DIR, 'camera_testing', 'webcams.db')


def main():
    csv.field_size_limit(2**31 - 1)

    # Backup existing DB
    if os.path.exists(DB_PATH):
        backup = DB_PATH + f'.backup_{int(time.time())}'
        os.rename(DB_PATH, backup)
        print(f'[CSV->SQLite] Old DB backed up to {backup}', flush=True)

    # Read CSV
    print(f'[CSV->SQLite] Reading {CSV_PATH}...', flush=True)
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    print(f'  Read {len(rows):,} rows × {len(header)} cols', flush=True)

    # Create DB
    print(f'[CSV->SQLite] Creating {DB_PATH}...', flush=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Build schema with TEXT cols and indexes
    cols_sql = ', '.join(f'"{h}" TEXT' for h in header)
    c.execute(f'CREATE TABLE webcams ({cols_sql})')

    # Insert
    placeholders = ', '.join('?' for _ in header)
    print(f'[CSV->SQLite] Inserting {len(rows):,} rows...', flush=True)
    BATCH = 5000
    n_cols = len(header)
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i+BATCH]
        # Pad short rows with empty strings
        batch_fixed = []
        for r in batch:
            if len(r) < n_cols:
                r = r + [''] * (n_cols - len(r))
            elif len(r) > n_cols:
                r = r[:n_cols]
            batch_fixed.append(r)
        c.executemany(f'INSERT INTO webcams VALUES ({placeholders})', batch_fixed)
        conn.commit()
        if (i // BATCH) % 5 == 0:
            print(f'  {i+len(batch):,}/{len(rows):,}', flush=True)

    # Indexes
    print(f'[CSV->SQLite] Creating indexes...', flush=True)
    if 'url' in header:
        c.execute('CREATE INDEX idx_url ON webcams(url)')
    if 'host' in header:
        c.execute('CREATE INDEX idx_host ON webcams(host)')
    if 'project_name' in header:
        c.execute('CREATE INDEX idx_project ON webcams(project_name)')
    if 'country' in header:
        c.execute('CREATE INDEX idx_country ON webcams(country)')
    if 'live_status' in header:
        c.execute('CREATE INDEX idx_live ON webcams(live_status)')

    conn.commit()
    conn.close()
    size = os.path.getsize(DB_PATH) / 1024 / 1024
    print(f'[CSV->SQLite] Done! DB size: {size:.1f} MB', flush=True)


if __name__ == '__main__':
    main()
