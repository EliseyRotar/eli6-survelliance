"""Deduplicate CSV rows. Safe to run while writers are running.

Strategy:
1. Read the current CSV (with retry)
2. Build seen set
3. While holding the lock file with O_EXCL (atomic create), do the dedup
4. Use lock file as serialize point — but writers also serialize there
5. After dedup, write back
"""
import csv
import os
import sys
import time

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
LOCK_PATH = CSV_PATH + '.lock'


def main():
    is_windows = sys.platform.startswith('win')
    # First check for stale lock and clear if older than 60s
    if os.path.exists(LOCK_PATH):
        try:
            age = time.time() - os.stat(LOCK_PATH).st_mtime
            if age > 60:
                os.remove(LOCK_PATH)
                print(f'cleared stale lock (age {age:.0f}s)', flush=True)
        except Exception:
            pass
    # Hold the lock
    for attempt in range(80):
        try:
            lock_fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            break
        except FileExistsError:
            time.sleep(0.05 + 0.03 * (attempt % 10))
    else:
        # Try once more after clearing stale
        try:
            age = time.time() - os.stat(LOCK_PATH).st_mtime
            if age > 30:
                os.remove(LOCK_PATH)
                try:
                    lock_fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                except Exception:
                    print('Failed to acquire lock; aborting', flush=True)
                    return
            else:
                print('Failed to acquire lock; aborting', flush=True)
                return
        except Exception:
            print('Failed to acquire lock; aborting', flush=True)
            return

    try:
        # Read with retry (writers may be flushing)
        rows = None
        for ra in range(8):
            try:
                with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
                    rows = list(csv.reader(f))
                break
            except PermissionError:
                time.sleep(0.2 + 0.1 * ra)
        if rows is None:
            print('read failed', flush=True)
            return
        print(f'read {len(rows)} rows', flush=True)

        header = rows[0]
        data = rows[1:]
        seen = {}
        removed = 0
        for r in data:
            url = (r[3] if len(r) > 3 else '').strip().lower()
            if not url:
                # empty-url row: prefer to keep if it has geo, else mark for rem if dup
                continue
            # live_status is column 9 (idx 9)
            is_dead = len(r) > 9 and r[9].strip() == 'dead'
            if url in seen:
                cur = seen[url]
                cur_dead = len(cur) > 9 and cur[9].strip() == 'dead'
                cur_score = sum(1 for i in (14, 19, 20, 21, 26) if len(cur) > i and cur[i].strip())
                new_score = sum(1 for i in (14, 19, 20, 21, 26) if len(r) > i and r[i].strip())
                # Prefer dead rows over live ones (don't want to keep live cams when dead was found)
                if cur_dead and not is_dead:
                    pass  # Keep dead
                elif is_dead and not cur_dead:
                    seen[url] = r  # Replace live with dead
                elif new_score > cur_score:
                    seen[url] = r
                removed += 1
            else:
                seen[url] = r

        # Re-number
        new_rows = [header]
        for i, r in enumerate(seen.values(), start=1):
            r[0] = str(i)
            new_rows.append(r)

        # Write atomically
        tmp_path = CSV_PATH + '.tmp'
        for wa in range(8):
            try:
                with open(tmp_path, 'w', encoding='utf-8', newline='') as f:
                    w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
                    for r in new_rows:
                        w.writerow(r)
                os.replace(tmp_path, CSV_PATH)
                break
            except PermissionError:
                time.sleep(0.3 + 0.2 * wa)
        print(f'before: {len(data)}, after dedup: {len(new_rows)-1}, removed: {removed}', flush=True)
    finally:
        try:
            os.close(lock_fd)
        except Exception:
            pass
        try:
            os.remove(LOCK_PATH)
        except OSError:
            pass


if __name__ == '__main__':
    main()
