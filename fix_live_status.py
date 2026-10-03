"""
Fix stray live_status values. Some ingestion scripts put text in live_status.
"""
import sqlite3
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DB = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\cams.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

# Find invalid live_status values
valid = ('live', 'unknown', 'auth_required', 'dead', 'offline', '')
cur.execute("SELECT DISTINCT live_status FROM cams WHERE live_status NOT IN (?, ?, ?, ?, ?, ?)", valid + ('',) if '' not in valid else valid)
bad = [r[0] for r in cur.fetchall() if r[0] not in valid]
print(f'Bad live_status values: {len(bad)}')
for b in bad:
    print(f'  {repr(b)}')

# Reset them to 'unknown'
for val in bad:
    cur.execute("UPDATE cams SET live_status='unknown' WHERE live_status=?", (val,))
conn.commit()
print('Fixed.')
