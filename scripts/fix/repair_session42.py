"""CSV field repairs for Session 42 (run AFTER ingestors are stopped).

Fixes (column-scoped, no row removal, no other fields touched):
  1. JSON-escaped URLs:  https:\/\/x  ->  https://x   in url + live_stream_url
  2. live_stream_url holds non-URL junk ('video','image', text) and url is a
     valid URL  ->  live_stream_url := url
  3. url non-empty but not a URL scheme -> url := '' ; if live then also invalid
     -> live_stream_url := ''
  4. visible junk image rows (logo/qrcode/banner in URL AND ends .png/.gif/.svg)
     -> flagged for deletion only if idx in KNOWN_JUNK (explicit list)

Backup first: backups/session42_<ts>/controllable_Webcams.csv
Atomic os.replace; verifies row count before/after.
"""
import csv
import os
import shutil
import sys
import time

P = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
SCHEMES = ('http://', 'https://', 'rtsp://', 'rtsps://', 'mms://', 'rtmp://')
KNOWN_JUNK = {'238611'}  # QR code png ingested by netlas before filter fix


def is_url(v):
    return v.lower().startswith(SCHEMES)


def main():
    ts = time.strftime('%Y%m%d_%H%M%S')
    bdir = rf'C:\Users\eli6-admin\Documents\eli6-surveillance\backups\session42_{ts}'
    os.makedirs(bdir, exist_ok=True)
    shutil.copy2(P, os.path.join(bdir, 'controllable_Webcams.csv'))
    print(f'backup -> {bdir}')

    with open(P, encoding='utf-8', newline='') as f:
        rd = csv.reader(f)
        hdr = next(rd)
        rows = list(rd)
    n0 = len(rows)

    u_esc = u_live_junk = u_url_blank = u_live_blank = u_live_from_url = 0
    out = []
    removed = []
    for row in rows:
        if row and row[0] in KNOWN_JUNK:
            removed.append(row[0])
            continue
        if len(row) < 4:
            out.append(row)
            continue
        u, v = row[2], row[3]
        # 1. unescape JSON slashes
        if '\\/' in u:
            row[2] = u = u.replace('\\/', '/')
            u_esc += 1
        if '\\/' in v:
            row[3] = v = v.replace('\\/', '/')
            u_esc += 1
        # 3. url invalid -> clear
        if u and not is_url(u):
            row[2] = u = ''
            u_url_blank += 1
        # 2. live invalid -> fallback to url
        if v and not is_url(v):
            if u:
                row[3] = u
                u_live_from_url += 1
            else:
                row[3] = ''
                u_live_blank += 1
        out.append(row)

    tmp = P + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
        w.writerow(hdr)
        w.writerows(out)
    os.replace(tmp, P)

    with open(P, encoding='utf-8', newline='') as f:
        n1 = sum(1 for _ in f) - 1
    print(f'rows {n0} -> {n1} (expected {n0 - len(removed)})')
    if n1 != n0 - len(removed):
        print('ROW COUNT MISMATCH - restore from backup!')
        sys.exit(1)
    print(f'JSON-unescaped fields: {u_esc}')
    print(f'bad url cleared: {u_url_blank}')
    print(f'live_url := url: {u_live_from_url}')
    print(f'live_url cleared: {u_live_blank}')
    print(f'removed junk rows: {removed}')
    print('OK')


if __name__ == '__main__':
    main()
