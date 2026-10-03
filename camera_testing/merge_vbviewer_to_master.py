"""Merge vbviewer_ingest CSV into master controllable_Webcams.csv.

Skips duplicates by URL (existing rows in master CSV take priority).
Acquires the same lock as dedup_csv.py to avoid race conditions.
"""

import os
import csv
import re
import time

WORKDIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
VBVIEWER_CSV = os.path.join(WORKDIR, "controllable_Webcams_vbviewer.csv")
MASTER_CSV = os.path.join(WORKDIR, "controllable_Webcams.csv")


def read_csv_header(path):
    """Read just the header line from a CSV file."""
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            header_line = f.readline().strip()
            return header_line.split(",")
    except Exception as e:
        print(f"Read header error: {e}", file=sys.stderr)
        return []


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


def get_master_next_idx():
    if not os.path.exists(MASTER_CSV):
        return 1
    last = 0
    try:
        with open(MASTER_CSV, "r", encoding="utf-8", errors="replace") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 32768), 0)
            for line in f.readlines()[-200:]:
                m = re.match(r"^(\d+),", line)
                if m:
                    last = max(last, int(m.group(1)))
    except Exception:
        pass
    return last + 1


def main():
    print(f"[VB Merge] Reading VBViewer CSV: {VBVIEWER_CSV}")
    vb_rows, vb_header = read_csv(VBVIEWER_CSV)
    print(f"[VB Merge] VBViewer rows: {len(vb_rows)}")

    print(f"[VB Merge] Reading master CSV: {MASTER_CSV}")
    master_rows, master_header = read_csv(MASTER_CSV)
    print(f"[VB Merge] Master rows: {len(master_rows)}")

    # Build set of existing URLs in master
    existing_urls = set()
    for row in master_rows:
        u = row.get("url", "").strip()
        if u:
            existing_urls.add(u)

    # Build set of vbviewer URLs to dedup within VBViewer CSV
    vb_urls = set()
    new_rows = []
    duplicates_in_vb = 0
    duplicates_in_master = 0
    for row in vb_rows:
        u = row.get("url", "").strip()
        if not u:
            continue
        if u in vb_urls:
            duplicates_in_vb += 1
            continue
        vb_urls.add(u)
        if u in existing_urls:
            duplicates_in_master += 1
            continue
        new_rows.append(row)

    print(f"[VB Merge] Duplicates within VBViewer CSV: {duplicates_in_vb}")
    print(f"[VB Merge] Already in master CSV: {duplicates_in_master}")
    print(f"[VB Merge] New rows to merge: {len(new_rows)}")

    if not new_rows:
        print("[VB Merge] Nothing to merge.")
        return

    # Renumber idx to avoid collisions
    next_idx = get_master_next_idx()
    for row in new_rows:
        row["idx"] = next_idx
        next_idx += 1

    # Acquire dedup lock to avoid race with dedup_csv.py
    LOCK_PATH = MASTER_CSV + ".lock"
    for attempt in range(80):
        try:
            lock_fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            break
        except FileExistsError:
            time.sleep(0.05 + 0.03 * (attempt % 10))
    else:
        # Force-clear stale lock
        try:
            age = time.time() - os.stat(LOCK_PATH).st_mtime
            if age > 60:
                os.remove(LOCK_PATH)
                lock_fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            else:
                print(f"[VB Merge] Could not acquire lock (held {age:.0f}s). Retrying...")
                time.sleep(2)
                lock_fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_RDWR)
        except Exception as e:
            print(f"[VB Merge] Lock acquire failed: {e}")
            return

    try:
        # Append to master CSV (read header fresh from file to avoid stale ref)
        actual_header = read_csv_header(MASTER_CSV)
        if not actual_header:
            actual_header = master_header
        try:
            with open(MASTER_CSV, "a", encoding="utf-8", newline="") as f:
                w = csv.writer(f, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
                for row in new_rows:
                    w.writerow([row.get(k, "") for k in actual_header])
            print(f"[VB Merge] Appended {len(new_rows)} rows to master CSV.")
        except Exception as e:
            print(f"[VB Merge] Error appending: {e}")
            return
    finally:
        try:
            os.close(lock_fd)
            os.remove(LOCK_PATH)
        except Exception:
            pass

    # Audit
    print(f"\n[VB Merge] Master CSV now has {len(master_rows) + len(new_rows) + 1} rows (incl. header)")
    # Count new entries by country
    from collections import Counter
    country_counts = Counter(row.get("country", "") for row in new_rows)
    print("New cams by country:")
    for c, n in sorted(country_counts.items(), key=lambda x: -x[1]):
        print(f"  {c}: {n}")
    live_counts = Counter(row.get("live_status", "") for row in new_rows)
    print("\nLive status:")
    for s, n in live_counts.items():
        print(f"  {s}: {n}")


if __name__ == "__main__":
    main()
