"""Webcam DB query tool - fast SQLite-backed queries.

Examples:
  python query_webcams.py --country "United States" --limit 20
  python query_webcams.py --host "62.96" --limit 10
  python query_webcams.py --video-only --live --limit 50
  python query_webcams.py --format m3u8 --limit 30
  python query_webcams.py --search "Hikvision" --limit 20
  python query_webcams.py --private --country Italy --limit 30
  python query_webcams.py --stats
  python query_webcams.py --dedup --out controllable_Webcams_dedup.csv
"""
import argparse
import csv
import os
import sys
import sqlite3

DB_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\webcams.db'
CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'


def get_header():
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        return next(csv.reader(f))


def query(args):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    where = []
    params = []

    if args.country:
        where.append('country = ?')
        params.append(args.country)
    if args.city:
        where.append('city LIKE ?')
        params.append(f'%{args.city}%')
    if args.host:
        where.append('host LIKE ?')
        params.append(f'%{args.host}%')
    if args.search:
        where.append('(url LIKE ? OR live_stream_url LIKE ? OR project_name LIKE ? OR org LIKE ? OR notes LIKE ? OR brand LIKE ?)')
        s = f'%{args.search}%'
        params.extend([s, s, s, s, s, s])
    if args.format == 'm3u8':
        where.append("live_stream_url LIKE '%.m3u8%'")
    elif args.format == 'mp4':
        where.append("live_stream_url LIKE '%.mp4%'")
    elif args.format == 'mjpeg':
        where.append("(live_stream_url LIKE '%mjpeg%' OR live_stream_url LIKE '%mjpg%')")
    elif args.format == 'jpg':
        where.append("live_stream_url LIKE '%.jpg%'")
    if args.video_only:
        where.append("(live_stream_url LIKE '%.m3u8%' OR live_stream_url LIKE '%.mp4%' OR live_stream_url LIKE '%mjpeg%')")
    if args.live:
        where.append("live_status = 'live'")
    if args.private:
        where.append("category = 'private'")
    if args.source:
        where.append("notes LIKE ?")
        params.append(f'%{args.source}_id=%')

    sql = 'SELECT * FROM webcams'
    if where:
        sql += ' WHERE ' + ' AND '.join(where)
    sql += f' LIMIT {args.limit}'

    rows = cur.execute(sql, params).fetchall()
    if args.out:
        with open(args.out, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
            w.writerow(get_header())
            for r in rows:
                w.writerow(r)
        print(f'Wrote {len(rows)} rows to {args.out}')
    else:
        header = get_header()
        # Pretty print
        for r in rows[:args.limit]:
            row_dict = dict(zip(header, r))
            print(f'\n[{row_dict["idx"]}] {row_dict["project_name"]} ({row_dict["country"]}/{row_dict["city"]})')
            print(f'  URL: {row_dict["live_stream_url"]}')
            if row_dict.get('org'):
                print(f'  Org: {row_dict["org"]}')
            if row_dict.get('brand'):
                print(f'  Brand: {row_dict["brand"]}')
            print(f'  Type: {row_dict["type"]} | Status: {row_dict["live_status"]}')
    return rows


def stats(args):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    print(f'Total rows: {cur.execute("SELECT COUNT(*) FROM webcams").fetchone()[0]:,}')
    print(f'Unique hosts: {cur.execute("SELECT COUNT(DISTINCT host) FROM webcams").fetchone()[0]:,}')
    print(f'Unique URLs: {cur.execute("SELECT COUNT(DISTINCT live_stream_url) FROM webcams WHERE live_stream_url != \"\" ").fetchone()[0]:,}')
    print(f'Live: {cur.execute("SELECT COUNT(*) FROM webcams WHERE live_status=\"live\"").fetchone()[0]:,}')
    print(f'Private/Residential: {cur.execute("SELECT COUNT(*) FROM webcams WHERE category=\"private\"").fetchone()[0]:,}')
    print()
    print('Top countries:')
    for c, n in cur.execute('SELECT country, COUNT(*) FROM webcams GROUP BY country ORDER BY 2 DESC LIMIT 15'):
        print(f'  {c}: {n:,}')
    print()
    print('Top orgs:')
    for o, n in cur.execute('SELECT org, COUNT(*) FROM webcams WHERE org != "" GROUP BY org ORDER BY 2 DESC LIMIT 15'):
        print(f'  {o}: {n:,}')
    print()
    print('Stream formats:')
    for fmt, n in cur.execute("""SELECT
        CASE
          WHEN live_stream_url LIKE '%.m3u8%' THEN 'HLS .m3u8'
          WHEN live_stream_url LIKE '%.mp4%' THEN 'MP4'
          WHEN live_stream_url LIKE '%mjpeg%' OR live_stream_url LIKE '%mjpg%' THEN 'MJPEG'
          WHEN live_stream_url LIKE '%.jpg%' OR live_stream_url LIKE '%.jpeg%' THEN 'JPEG'
          ELSE 'other'
        END as fmt, COUNT(*)
      FROM webcams WHERE live_stream_url != '' GROUP BY fmt ORDER BY 2 DESC"""):
        print(f'  {fmt}: {n:,}')


def dedup(args):
    """Deduplicate by live_stream_url (already done by dedup_csv.py, this is a different version)."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    print('Counting duplicates...')
    dups = cur.execute("""
        SELECT live_stream_url, COUNT(*) as n FROM webcams
        WHERE live_stream_url != ''
        GROUP BY live_stream_url
        HAVING n > 1
        ORDER BY n DESC LIMIT 30
    """).fetchall()
    for url, n in dups:
        print(f'  {n}x: {url[:100]}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--country')
    parser.add_argument('--city')
    parser.add_argument('--host')
    parser.add_argument('--search')
    parser.add_argument('--format', choices=['m3u8', 'mp4', 'mjpeg', 'jpg'])
    parser.add_argument('--video-only', action='store_true')
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--private', action='store_true')
    parser.add_argument('--source')
    parser.add_argument('--limit', type=int, default=20)
    parser.add_argument('--out', help='Output CSV path')
    parser.add_argument('--stats', action='store_true')
    parser.add_argument('--dedup', action='store_true')
    args = parser.parse_args()
    if args.stats:
        stats(args)
    elif args.dedup:
        dedup(args)
    else:
        query(args)


if __name__ == '__main__':
    main()
