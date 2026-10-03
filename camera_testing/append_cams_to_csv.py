#!/usr/bin/env python3
"""
Append newly discovered cams to controllable_Webcams.csv.
DOES NOT MODIFY EXISTING ROWS - only appends new rows at the end.
"""
import csv
import io

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'

# New cams to append
NEW_CAMS = [
    # ---- Daytona Beach (ERAU) flight cams (NEW DISCOVERY) ----
    ('flightcamnorth.db.erau.edu', 'erau006', 'ERAU Daytona Beach Flightcam NORTH - AXIS M2025-LE bullet (Daytona Beach Intl Airport, native H.264, no MJPEG auth)', 'http://flightcamnorth.db.erau.edu/'),
    ('flightcamnorth.db.erau.edu', 'erau007', 'ERAU Daytona Beach Flightcam NORTH - Live MJPEG Stream', 'http://flightcamnorth.db.erau.edu/axis-cgi/mjpg/video.cgi'),
    ('flightcamnorth.db.erau.edu', 'erau008', 'ERAU Daytona Beach Flightcam NORTH - Live H.264 Stream (Matroska, 1280x720, Main profile)', 'http://flightcamnorth.db.erau.edu/axis-cgi/media.cgi?container=matroska&videocodec=h264&resolution=1280x720'),
    ('flightcamnorth.db.erau.edu', 'erau009', 'ERAU Daytona Beach Flightcam NORTH - HTTPS variant', 'https://flightcamnorth.db.erau.edu/'),
    ('flightcamsouth.db.erau.edu', 'erau010', 'ERAU Daytona Beach Flightcam SOUTH - AXIS M2025-LE bullet (Daytona Beach Intl Airport, native H.264, no MJPEG auth)', 'http://flightcamsouth.db.erau.edu/'),
    ('flightcamsouth.db.erau.edu', 'erau011', 'ERAU Daytona Beach Flightcam SOUTH - Live MJPEG Stream', 'http://flightcamsouth.db.erau.edu/axis-cgi/mjpg/video.cgi'),
    ('flightcamsouth.db.erau.edu', 'erau012', 'ERAU Daytona Beach Flightcam SOUTH - Live H.264 Stream (Matroska, 1280x720, Main profile)', 'http://flightcamsouth.db.erau.edu/axis-cgi/media.cgi?container=matroska&videocodec=h264&resolution=1280x720'),
    ('flightcamsouth.db.erau.edu', 'erau013', 'ERAU Daytona Beach Flightcam SOUTH - HTTPS variant', 'https://flightcamsouth.db.erau.edu/'),
    # ---- DB cams DNS exists but ports closed (for historical record) ----
    ('cam.db.erau.edu', 'erau014', 'ERAU Daytona Beach cam.db.erau.edu - DNS exists but offline (155.31.10.219 firewalled)', 'http://cam.db.erau.edu/'),
    ('cam1.db.erau.edu', 'erau015', 'ERAU Daytona Beach cam1.db.erau.edu - DNS exists but offline (155.31.10.217 firewalled)', 'http://cam1.db.erau.edu/'),
    ('cam2.db.erau.edu', 'erau016', 'ERAU Daytona Beach cam2.db.erau.edu - DNS exists but offline (155.31.10.218 firewalled)', 'http://cam2.db.erau.edu/'),
    # ---- Prescott sibling cams (DNS exists but offline) ----
    ('flightcam1.pr.erau.edu', 'erau017', 'ERAU Prescott Flightcam 1 - MJPEG via custom resolution (1280x720)', 'http://flightcam1.pr.erau.edu/mjpg/video.mjpg?resolution=1280x720'),
    ('flightcam1.pr.erau.edu', 'erau018', 'ERAU Prescott Flightcam 1 - Single JPEG snapshot (1280x720)', 'http://flightcam1.pr.erau.edu/axis-cgi/jpg/image.cgi?resolution=1280x720'),
    ('flightcam1.pr.erau.edu', 'erau019', 'ERAU Prescott Flightcam 1 - H.264 RTSP endpoint (port 554 firewalled externally, accessible on internal networks)', 'rtsp://flightcam1.pr.erau.edu:554/axis-media/media.amp'),
]


def make_row(domain, post_id, title, url, author='nolandda', subreddit_id='t5_2qt74'):
    created_utc = 1787313600.0
    permalink = f'http://www.reddit.com/r/controllablewebcams/comments/{post_id}/'
    return [
        f'{created_utc}', '1', domain, post_id, title, author, '1', '0', '0',
        permalink, '', '', 'False', '', subreddit_id, 'False', '', '', 'False',
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
            print(f'[!] SKIP duplicate: {domain}/{post_id}')
            continue
        row = make_row(domain, post_id, title, url)
        new_rows.append(row)
        print(f'[+] Add: {domain}/{post_id}')
    
    if not new_rows:
        print('[+] No new rows to add.')
        return
    
    with open(CSV_PATH, 'ab') as f:
        for row in new_rows:
            buf = io.StringIO()
            writer = csv.writer(buf, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(row)
            f.write(buf.getvalue().encode('utf-8'))
    
    print(f'[+] Appended {len(new_rows)} new rows')
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        total = sum(1 for _ in f)
    print(f'[+] Total rows now: {total}')


if __name__ == '__main__':
    main()