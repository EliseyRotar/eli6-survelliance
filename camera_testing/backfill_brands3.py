"""Backfill brand/model for empty-brand rows using more advanced patterns."""

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
    print(f"[Brand Backfill 3] Reading {MASTER_CSV}")
    with open(MASTER_CSV, "r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.reader(f)
        header = next(r)
        rows = []
        for row in r:
            if len(row) < len(header):
                row += [""] * (len(header) - len(row))
            rows.append(dict(zip(header, row)))

    updated = 0
    for row in rows:
        if (row.get("brand") or "").strip():
            continue
        notes = row.get("notes", "") or ""
        url = row.get("url", "") or ""
        live_url = row.get("live_stream_url", "") or ""

        # Pattern 1: opencctv_id= in notes
        if "opencctv_id=" in notes:
            # Extract source from opencctv_id
            m = re.search(r'opencctv_id=([^;,\s]+)', notes)
            if m:
                ocid = m.group(1)
                # Determine subtype
                if 'cr-' in ocid or 'castle' in ocid.lower():
                    row["brand"] = "OpenCCTV (Castle Rock)"
                elif 'cotrip' in ocid.lower():
                    row["brand"] = "OpenCCTV (CDOT)"
                elif 'nvroads' in ocid.lower():
                    row["brand"] = "OpenCCTV (Nevada DOT)"
                elif 'indot' in ocid.lower():
                    row["brand"] = "OpenCCTV (INDOT)"
                elif 'fl511' in ocid.lower():
                    row["brand"] = "OpenCCTV (FL511)"
                elif 'hctx' in ocid.lower() or 'houston' in ocid.lower():
                    row["brand"] = "OpenCCTV (Houston)"
                else:
                    row["brand"] = "OpenCCTV"
                updated += 1
            else:
                row["brand"] = "OpenCCTV"
                updated += 1
            continue

        # Pattern 2: URL has recognizable vendor name
        url_lower = url.lower()
        if 'nvroads' in url_lower:
            row["brand"] = "Nevada DOT"
            updated += 1
        elif 'trakit' in url_lower:
            row["brand"] = "TrakIt"
            updated += 1
        elif 'dot511' in url_lower:
            row["brand"] = "DOT511"
            updated += 1
        elif 'tripcheck' in url_lower:
            row["brand"] = "TripCheck"
            updated += 1
        elif '511on' in url_lower:
            row["brand"] = "511ON"
            updated += 1
        elif 'wzmedia' in url_lower or 'caltrans' in url_lower:
            row["brand"] = "Caltrans"
            updated += 1
        elif 'windalert' in url_lower:
            row["brand"] = "WindAlert"
            updated += 1
        elif 'webcams.nyctmc' in url_lower:
            row["brand"] = "NYCTMC"
            updated += 1
        elif '511ga' in url_lower:
            row["brand"] = "511GA"
            updated += 1
        elif '511' in url_lower:
            row["brand"] = "511"
            updated += 1
        elif 'cctv.' in url_lower or 'cam.river.go.jp' in url_lower:
            row["brand"] = "Government CCTV"
            updated += 1
        # Pattern 3: live_stream_url has .m3u8 - usually trafficvision
        elif '.m3u8' in live_url and 'localhost' not in live_url:
            row["brand"] = "TrafficVision"
            updated += 1
        # Pattern 4: specific patterns in notes
        elif 'wetmet' in notes.lower():
            row["brand"] = "WetMet"
            updated += 1
        elif 'balticlivecam' in notes.lower():
            row["brand"] = "BalticLiveCam"
            updated += 1
        elif 'angelcam' in notes.lower():
            row["brand"] = "AngelCam"
            updated += 1
        elif 'whep' in notes.lower():
            row["brand"] = "WHEP"
            updated += 1
        # Pattern 5: page_title has clues
        elif (page_title := row.get("page_title", "")):
            if 'VB-M' in page_title or 'VB-S' in page_title or 'VB-' in page_title:
                row["brand"] = "Canon"
                # Extract model
                m = re.search(r'(VB-[A-Z]?\d+[A-Z]*)', page_title)
                if m:
                    row["model"] = m.group(1)
                updated += 1
            elif 'Panasonic' in page_title:
                row["brand"] = "Panasonic"
                updated += 1
            elif 'i-PRO' in page_title:
                row["brand"] = "i-PRO"
                updated += 1
            elif 'Hikvision' in page_title or 'HIKVISION' in page_title:
                row["brand"] = "Hikvision"
                updated += 1
            elif 'AXIS' in page_title or 'Axis' in page_title:
                row["brand"] = "Axis"
                updated += 1
            elif 'Dahua' in page_title:
                row["brand"] = "Dahua"
                updated += 1

    print(f"[Brand Backfill 3] Updated {updated:,} rows")

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
        print(f"[Brand Backfill 3] Wrote {len(rows):,} rows to master CSV")
    finally:
        try:
            os.close(lock_fd)
            os.remove(LOCK_PATH)
        except Exception:
            pass


if __name__ == "__main__":
    main()
