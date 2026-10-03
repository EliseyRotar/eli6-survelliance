"""Update existing master CSV rows for VB cams with MJPEG URLs.

Reads the VB cam CSV (which has updated MJPEG URLs), then goes through master CSV
and updates matching rows by URL.
"""

import os
import sys
import csv
import re
import time

WORKDIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
VB_CSV = os.path.join(WORKDIR, "controllable_Webcams_vbviewer.csv")
MASTER_CSV = os.path.join(WORKDIR, "controllable_Webcams.csv")
LOCK_PATH = MASTER_CSV + ".lock"


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


def read_csv(path):
    csv.field_size_limit(2**31 - 1)
    rows = []
    if not os.path.exists(path):
        return rows, []
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.reader(f)
        header = next(r, None)
        if not header:
            return rows, []
        for row in r:
            if len(row) < len(header):
                row += [""] * (len(header) - len(row))
            rows.append(dict(zip(header, row)))
    return rows, header


def main():
    print(f"[VB Update Master] Reading VB CSV: {VB_CSV}")
    vb_rows, vb_header = read_csv(VB_CSV)
    url_to_mjpeg = {}
    for row in vb_rows:
        url = row.get("url", "")
        mjpeg_url = row.get("live_stream_url", "")
        if url and "localhost:8767" in mjpeg_url:
            url_to_mjpeg[url] = mjpeg_url
    print(f"[VB Update Master] {len(url_to_mjpeg)} cams with MJPEG URLs")

    print(f"[VB Update Master] Reading master CSV: {MASTER_CSV}")
    master_rows, master_header = read_csv(MASTER_CSV)
    print(f"[VB Update Master] Master rows: {len(master_rows)}")

    updated = 0
    for row in master_rows:
        url = row.get("url", "")
        if url in url_to_mjpeg:
            new_url = url_to_mjpeg[url]
            old = row.get("live_stream_url", "")
            if old != new_url:
                row["live_stream_url"] = new_url
                row["type"] = "video-mjpeg"
                notes = row.get("notes", "") or ""
                if "mjpeg_url=" not in notes:
                    notes = (notes + f" | mjpeg_url={new_url}").strip(" |")
                    row["notes"] = notes
                updated += 1

    print(f"[VB Update Master] Updated {updated} existing rows")

    if updated == 0:
        return

    lock_fd = acquire_lock()
    try:
        tmp_path = MASTER_CSV + ".tmp"
        with open(tmp_path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
            w.writerow(master_header)
            for row in master_rows:
                w.writerow([row.get(k, "") for k in master_header])
        os.replace(tmp_path, MASTER_CSV)
        print(f"[VB Update Master] Wrote {len(master_rows)} rows to master CSV")
    finally:
        try:
            os.close(lock_fd)
            os.remove(LOCK_PATH)
        except Exception:
            pass


if __name__ == "__main__":
    main()
