"""Check webcams.db structure."""
import sqlite3

p = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\webcams.db'
conn = sqlite3.connect(p)
cur = conn.cursor()

# List tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
print('Tables:', tables)

# Get row count and schema
for table_name, in tables:
    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cur.fetchone()[0]
    cur.execute(f"PRAGMA table_info({table_name})")
    cols = cur.fetchall()
    print(f'\n{table_name}: {count:,} rows')
    print(f'  Columns: {len(cols)}')
    for c in cols[:5]:
        print(f'    {c}')
    if len(cols) > 5:
        print(f'    ... +{len(cols)-5} more')

# Sample
print('\nSample row:')
cur.execute("SELECT * FROM cams LIMIT 1" if ('cams',) in tables else "SELECT * FROM webcams LIMIT 1")
row = cur.fetchone()
if row:
    print(f'  {row[:10]}...')
