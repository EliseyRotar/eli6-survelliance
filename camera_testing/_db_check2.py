import sqlite3, os, sys
DB_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\webcams.db'
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
print('Total:', cur.execute('SELECT COUNT(*) FROM webcams').fetchone()[0])
q = 'SELECT COUNT(DISTINCT live_stream_url) FROM webcams WHERE live_stream_url IS NOT NULL AND live_stream_url != ?'
print('Unique live URLs:', cur.execute(q, ('',)).fetchone()[0])
print()
print('By country top 20:')
for c, n in cur.execute('SELECT country, COUNT(*) FROM webcams GROUP BY country ORDER BY 2 DESC LIMIT 20'):
    # Sanitize for ASCII output
    cs = c.encode('ascii', 'replace').decode() if c else 'NULL'
    print(' ', cs, n)
conn.close()
