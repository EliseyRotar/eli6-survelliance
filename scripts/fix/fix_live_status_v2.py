"""Fix last stray live_status values."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import sqlite3
DB = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\cams.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()
valid = ('live', 'unknown', 'auth_required', 'dead', 'offline', '', 'True', '200')
cur.execute("SELECT DISTINCT live_status FROM cams WHERE live_status NOT IN (?, ?, ?, ?, ?, ?, ?, ?)", valid)
bad = [r[0] for r in cur.fetchall() if r[0] not in valid]
print(f'Bad live_status values: {len(bad)}')
for b in bad:
    print(f'  {repr(b)}')
for val in bad:
    cur.execute("UPDATE cams SET live_status='unknown' WHERE live_status=?", (val,))
conn.commit()
print('Fixed.')
