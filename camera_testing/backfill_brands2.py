"""Backfill brand/model for rows that have empty brand but contain 'trafficvision_id='."""

import os
import csv
import re
import time

WORKDIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
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


def main():
    csv.field_size_limit(2**31 - 1)
    print(f"[Brand Backfill 2] Reading {MASTER_CSV}")
    rows = []
    with open(MASTER_CSV, "r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.reader(f)
        header = next(r)
        for row in r:
            if len(row) < len(header):
                row += [""] * (len(header) - len(row))
            rows.append(dict(zip(header, row)))

    print(f"[Brand Backfill 2] {len(rows):,} rows")

    updated = 0
    patterns_added = 0
    for row in rows:
        if row.get("brand", "").strip():
            continue
        notes = row.get("notes", "") or ""

        # Pattern 1: trafficvision_id=...
        if "trafficvision_id=" in notes:
            row["brand"] = "TrafficVision"
            # Try to extract model from notes
            feed_type_m = re.search(r'feedType=(\w+)', notes)
            if feed_type_m:
                row["model"] = feed_type_m.group(1).upper()
            updated += 1
            patterns_added += 1
            continue

        # Pattern 2: opencctv_id=...
        if "opencctv_id=" in notes:
            row["brand"] = "OpenCCTV"
            updated += 1
            patterns_added += 1
            continue

        # Pattern 3: tfl-jamcam (TFL cams)
        if "tfl" in notes.lower() or "jamcam" in notes.lower():
            row["brand"] = "TfL JamCam"
            updated += 1
            patterns_added += 1
            continue

        # Pattern 4: vbviewer_id (Canon VB cams)
        if "vbviewer_id=" in notes:
            # Try to extract model
            model_m = re.search(r'model=(VB-[A-Z]?\d+[A-Z]*)', notes)
            if model_m:
                row["model"] = model_m.group(1)
            else:
                # Extract from description
                desc = row.get("description", "") or ""
                vb_m = re.search(r'(VB-[A-Z]?\d+[A-Z]*)', desc)
                if vb_m:
                    row["model"] = vb_m.group(1)
            row["brand"] = "Canon"
            updated += 1
            patterns_added += 1
            continue

        # Pattern 5: live_env or windy.com
        if "live_env" in notes or "windy" in notes.lower():
            row["brand"] = "Live Env" if "live_env" in notes else "Windy.com"
            updated += 1
            patterns_added += 1
            continue

        # Pattern 6: Generic i-PRO/Panasonic/Canon from server header
        server = row.get("server_header", "") or ""
        if "VB" == server:
            row["brand"] = "Canon"
            updated += 1
            patterns_added += 1
            continue
        if "i-PRO" in server or "i-pro" in server.lower():
            row["brand"] = "i-PRO"
            updated += 1
            patterns_added += 1
            continue

    print(f"[Brand Backfill 2] Updated {updated:,} rows ({patterns_added} pattern-matched)")

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
        print(f"[Brand Backfill 2] Wrote {len(rows):,} rows to master CSV")
    finally:
        try:
            os.close(lock_fd)
            os.remove(LOCK_PATH)
        except Exception:
            pass


if __name__ == "__main__":
    main()
