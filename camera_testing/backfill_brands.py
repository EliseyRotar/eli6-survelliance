"""Backfill brand/model for existing master CSV rows that have empty brand.

Strategy:
- Parse notes to extract source info
- If notes contain 'source=argus-v3' or 'argus-v2', set brand='Argus Public Cams'
- If notes contain 'source=opencctv', set brand='OpenCCTV'
- If notes contain 'source=trafficvision', set brand='TrafficVision'
- If notes contain 'source=tfl-jamcam', set brand='TfL JamCam'
- etc.
"""

import os
import csv
import re
import time

WORKDIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
MASTER_CSV = os.path.join(WORKDIR, "controllable_Webcams.csv")
LOCK_PATH = MASTER_CSV + ".lock"

SOURCE_BRAND_MAP = {
    'argus-v2': 'Argus Public Cams',
    'argus-v3': 'Argus Public Cams',
    'argus': 'Argus Public Cams',
    'opencctv': 'OpenCCTV',
    'opencctv-cotrip': 'OpenCCTV (CDOT)',
    'opencctv-castlerock': 'OpenCCTV (Castle Rock)',
    'trafficvision': 'TrafficVision',
    'tfl-jamcam': 'TfL JamCam',
    'tfl': 'TfL JamCam',
    'caltrans': 'Caltrans',
    'netlas': 'Netlas',
    'live_env': 'Live Env',
    'live_env2': 'Live Env',
    'windy_com': 'Windy.com',
    'insecam_dump': 'Insecam',
    'mass_portscan': 'Mass Portscan',
    'full-reprobe': 'Full Reprobe',
    'mjpg_search': 'MJPEG Search',
    'user-provided': 'User Provided',
    'user-substream': 'User Substream',
    'user': 'User Provided',
    'vbviewer': 'Canon VBViewer',
}


def acquire_lock():
    for attempt in range(80):
        try:
            return os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_RDWR)
        except FileExistsError:
            time.sleep(0.05 + 0.03 * (attempt % 10))
    try:
        age = time.time() - os.stat(LOCK_PATH).st_mtime
        if age > 60:
            os.remove(LOCK_PATH)
            return os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_RDWR)
    except Exception:
        pass
    raise RuntimeError("Could not acquire lock")


def main():
    csv.field_size_limit(2**31 - 1)
    print(f"[Brand Backfill] Reading {MASTER_CSV}")
    rows = []
    with open(MASTER_CSV, "r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.reader(f)
        header = next(r)
        for row in r:
            if len(row) < len(header):
                row += [""] * (len(header) - len(row))
            rows.append(dict(zip(header, row)))

    print(f"[Brand Backfill] {len(rows):,} rows")

    updated = 0
    for row in rows:
        if row.get("brand", "").strip():
            continue  # Skip if brand already set
        notes = row.get("notes", "") or ""
        # Extract source from notes
        m = re.search(r'source=(\S+)', notes)
        if not m:
            continue
        source = m.group(1).rstrip(',;').rstrip()
        # Find matching brand
        for src_key, brand in SOURCE_BRAND_MAP.items():
            if source.startswith(src_key):
                row["brand"] = brand
                updated += 1
                break

    print(f"[Brand Backfill] Updated {updated:,} rows")

    if updated == 0:
        return

    lock_fd = acquire_lock()
    try:
        tmp_path = MASTER_CSV + ".tmp"
        with open(tmp_path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
            w.writerow(header)
            for row in rows:
                w.writerow([row.get(k, "") for k in header])
        os.replace(tmp_path, MASTER_CSV)
        print(f"[Brand Backfill] Wrote {len(rows):,} rows to master CSV")
    finally:
        try:
            os.close(lock_fd)
            os.remove(LOCK_PATH)
        except Exception:
            pass


if __name__ == "__main__":
    main()
