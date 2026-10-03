#!/usr/bin/env python3
"""Append db.erau.edu + sbhome + dartmouth cams to controllable_Webcams.csv"""
import csv, io

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'

NEW_CAMS = [
    # db.erau.edu (Daytona Beach)
    ('flightcamnorth.db.erau.edu', 'erau020', 'ERAU Daytona Beach Flightcam NORTH - AXIS M2025-LE, VAPIX param dump (full 812 lines accessible)', 'http://flightcamnorth.db.erau.edu/axis-cgi/param.cgi?action=list'),
    ('flightcamnorth.db.erau.edu', 'erau021', 'ERAU Daytona Beach Flightcam NORTH - HTTPS direct', 'https://flightcamnorth.db.erau.edu/view/index.shtml'),
    ('flightcamsouth.db.erau.edu', 'erau022', 'ERAU Daytona Beach Flightcam SOUTH - AXIS M2025-LE, VAPIX param dump', 'http://flightcamsouth.db.erau.edu/axis-cgi/param.cgi?action=list'),
    ('flightcamsouth.db.erau.edu', 'erau023', 'ERAU Daytona Beach Flightcam SOUTH - HTTPS direct', 'https://flightcamsouth.db.erau.edu/view/index.shtml'),
    # sbhome (private home cam)
    ('sbhome63378.dyndns.org', 'sbhome001', 'Private AXIS M2025-LE home cam (consumer dyndns, h264 enabled)', 'http://sbhome63378.dyndns.org:16251/'),
    ('sbhome63378.dyndns.org', 'sbhome002', 'Private home cam - MJPEG stream', 'http://sbhome63378.dyndns.org:16251/axis-cgi/mjpg/video.cgi'),
    ('sbhome63378.dyndns.org', 'sbhome003', 'Private home cam - Snapshot', 'http://sbhome63378.dyndns.org:16251/axis-cgi/jpg/image.cgi'),
    # dartmouth wc2 (Baker Library webcam)
    ('wc2.dartmouth.edu', 'dartmouth001', 'Dartmouth College WC2 cam - AXIS camera at Baker Library area', 'http://wc2.dartmouth.edu/'),
    ('wc2.dartmouth.edu', 'dartmouth002', 'Dartmouth WC2 - Live MJPEG stream', 'http://wc2.dartmouth.edu/mjpg/video.mjpg'),
    ('wc2.dartmouth.edu', 'dartmouth003', 'Dartmouth WC2 - Snapshot', 'http://wc2.dartmouth.edu/axis-cgi/jpg/image.cgi?resolution=1280x720'),
]


def make_row(domain, post_id, title, url):
    return [
        '1787313600.0', '1', domain, post_id, title, 'nolandda',
        '1', '0', '0',
        f'http://www.reddit.com/r/controllablewebcams/comments/{post_id}/',
        '', '', 'False', '', 't5_2qt74', 'False', '', '', 'False',
        f't3_{post_id}', url, ''
    ]


def main():
    existing = set()
    with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 21:
                existing.add((row[2], row[3]))
    
    print(f'[+] Loaded {len(existing)} existing rows')
    
    new_rows = []
    for domain, post_id, title, url in NEW_CAMS:
        if (domain, post_id) in existing:
            print(f'[!] SKIP dup: {domain}/{post_id}')
            continue
        new_rows.append(make_row(domain, post_id, title, url))
        print(f'[+] Add: {domain}/{post_id}')
    
    if not new_rows:
        return
    
    with open(CSV_PATH, 'ab') as f:
        for row in new_rows:
            buf = io.StringIO()
            csv.writer(buf, lineterminator='\n').writerow(row)
            f.write(buf.getvalue().encode('utf-8'))
    
    print(f'[+] Appended {len(new_rows)} rows')
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        total = sum(1 for _ in f)
    print(f'[+] Total: {total}')


if __name__ == '__main__':
    main()