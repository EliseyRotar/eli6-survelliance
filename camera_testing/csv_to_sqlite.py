"""Convert CSV to SQLite for fast queries + split into chunks for easy viewing.

The CSV is 50MB+ with 67k rows. Loading in Excel hangs. Solution:
- Convert to SQLite (queriable in any viewer)
- Split into per-row CSV chunks (each cam one .txt in cam_<IP>/ folder is already done)
- Generate per-state/per-country/per-source CSV subsets
"""
import csv
import os
import sys
import sqlite3
import time

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
DB_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\webcams.db'
CHUNKS_DIR = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\csv_chunks'

CHUNK_SIZE = 5000  # rows per file


def log(msg):
    print(f'[{time.strftime("%H:%M:%S")}] {msg}', flush=True)


def csv_to_sqlite():
    log(f'Starting SQLite conversion of {CSV_PATH}')
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Create table from header
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        reader = csv.reader(f)
        header = next(reader)
        cols = ','.join([f'"{c}" TEXT' for c in header])
        cur.execute(f'CREATE TABLE webcams ({cols})')
        # Index on common search columns
        cur.execute(f'CREATE INDEX idx_country ON webcams(country)')
        cur.execute(f'CREATE INDEX idx_brand ON webcams(brand)')
        cur.execute(f'CREATE INDEX idx_live_url ON webcams(live_stream_url)')
        cur.execute(f'CREATE INDEX idx_host ON webcams(host)')

        batch = []
        n = 0
        ncols = len(header)
        for row in reader:
            # Pad or truncate to match header
            if len(row) < ncols:
                row = row + [''] * (ncols - len(row))
            elif len(row) > ncols:
                row = row[:ncols]
            batch.append(row)
            n += 1
            if len(batch) >= 1000:
                placeholders = ','.join(['?'] * ncols)
                cur.executemany(f'INSERT INTO webcams VALUES ({placeholders})', batch)
                batch = []
                if n % 10000 == 0:
                    log(f'  inserted {n} rows')
        if batch:
            placeholders = ','.join(['?'] * ncols)
            cur.executemany(f'INSERT INTO webcams VALUES ({placeholders})', batch)
        conn.commit()
        log(f'Total rows: {n}')


def split_csv():
    log(f'Splitting CSV into chunks of {CHUNK_SIZE} rows')
    os.makedirs(CHUNKS_DIR, exist_ok=True)
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        reader = csv.reader(f)
        header = next(reader)
        chunk_n = 0
        batch = []
        rows_in_chunk = 0
        for row in reader:
            batch.append(row)
            rows_in_chunk += 1
            if rows_in_chunk >= CHUNK_SIZE:
                chunk_path = os.path.join(CHUNKS_DIR, f'webcams_{chunk_n:04d}.csv')
                with open(chunk_path, 'w', encoding='utf-8', newline='') as out:
                    w = csv.writer(out, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
                    w.writerow(header)
                    w.writerows(batch)
                chunk_n += 1
                batch = []
                rows_in_chunk = 0
                if chunk_n % 5 == 0:
                    log(f'  wrote chunk {chunk_n}')
        if batch:
            chunk_path = os.path.join(CHUNKS_DIR, f'webcams_{chunk_n:04d}.csv')
            with open(chunk_path, 'w', encoding='utf-8', newline='') as out:
                w = csv.writer(out, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
                w.writerow(header)
                w.writerows(batch)


if __name__ == '__main__':
    csv_to_sqlite()
    split_csv()
    log('Done')
