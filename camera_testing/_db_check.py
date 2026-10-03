import sqlite3, os, sys
DB_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\webcams.db'
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
print('Total:', cur.execute('SELECT COUNT(*) FROM webcams').fetchone()[0])
print('Indexes:')
for idx in cur.execute("SELECT name FROM sqlite_master WHERE type='index'"):
    print(' ', idx[0])
print('Unique live URLs:', cur.execute('SELECT COUNT(DISTINCT live_stream_url) FROM webcams WHERE live_stream_url IS NOT NULL AND live_stream_url != ""').fetchone()[0])
print()
print('By type:')
for t, n in cur.execute('SELECT type, COUNT(*) FROM webcams GROUP BY type ORDER BY 2 DESC LIMIT 10'):
    print(f'  {t}: {n}')
print()
print('By country top 10:')
for c, n in cur.execute('SELECT country, COUNT(*) FROM webcams GROUP BY country ORDER BY 2 DESC LIMIT 10'):
    print(f'  {c}: {n}')
conn.close()
