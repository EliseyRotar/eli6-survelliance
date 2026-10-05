"""ffmpeg-based poster extraction service.

For each HLS cam, uses ffmpeg to extract one frame and save as JPEG.
This gives every HLS tile a real preview image that loads instantly
(matches trafficvision.live's behavior).

Uses Win32 Job Objects for hard timeout enforcement. When a job handle
is closed, the kernel kills all processes in it (including any I/O-
blocked threads), bypassing Python's broken subprocess.TimeoutExpired
on Windows when the child is in kernel-mode TCP waits.

Outputs to web_viewer/static/posters/<idx>.jpg (served at /api/poster/<idx>)
"""
import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(line_buffering=True)

CSV_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')
OUT_DIR = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\web_viewer\static\posters')
PROGRESS = Path(r'C:\Users\eli6-admin\AppData\Local\Temp\poster_ffmpeg_progress.json')
LOG = Path(r'C:\Users\eli6-admin\AppData\Local\Temp\poster_ffmpeg.log')
FFMPEG = r'C:\Users\eli6-admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe'

OUT_DIR.mkdir(parents=True, exist_ok=True)

# Try to import Win32 job-object APIs
try:
    import win32job
    import win32api
    import win32con
    HAVE_JOB_OBJECTS = True
except ImportError:
    HAVE_JOB_OBJECTS = False
    print('WARNING: pywin32 not installed, falling back to taskkill timeout (less reliable)')


def log(msg, **kwargs):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def create_kill_job():
    """Create a Job Object that kills all assigned processes when the
    handle is closed. Returning the handle to the caller makes them
    responsible for closing it (and thereby killing the ffmpeg)."""
    if not HAVE_JOB_OBJECTS:
        return None
    job = win32job.CreateJobObject(None, '')
    info = win32job.QueryInformationJobObject(job, win32job.JobObjectExtendedLimitInformation)
    info['BasicLimitInformation']['LimitFlags'] = win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    win32job.SetInformationJobObject(job, win32job.JobObjectExtendedLimitInformation, info)
    return job


def assign_to_job(handle, job):
    """Assign an open process handle to a Job Object."""
    if not HAVE_JOB_OBJECTS or job is None or handle is None:
        return
    try:
        win32job.AssignProcessToJobObject(job, handle)
    except Exception as e:
        # May fail if process already exited
        pass


def extract_frame(idx, hls_url):
    """Extract a single frame from HLS stream as JPEG via ffmpeg in a Job Object.

    Writes result directly to PROGRESS so we don't depend on the main loop
    for status updates. The main loop batches writes every 25 results.
    """
    out_path = OUT_DIR / f'{idx}.jpg'
    if out_path.exists() and out_path.stat().st_size > 1000:
        mtime = time.time() - out_path.stat().st_mtime
        if mtime < 3600:
            return idx, True

    cmd = [
        FFMPEG,
        '-hide_banner',
        '-loglevel', 'error',
        '-timeout', '4000000',
        '-i', hls_url,
        '-ss', '00:00:01',
        '-vframes', '1',
        '-q:v', '5',
        '-vf', 'scale=480:-1',
        '-y',
        str(out_path),
    ]
    job = create_kill_job()
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=0x08000000,
        )
        if HAVE_JOB_OBJECTS and job is not None:
            try:
                proc_handle = win32api.OpenProcess(
                    win32con.PROCESS_TERMINATE | win32con.PROCESS_SET_QUOTA,
                    False, proc.pid
                )
                assign_to_job(proc_handle, job)
                win32api.CloseHandle(proc_handle)
            except Exception:
                pass

        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass

        if HAVE_JOB_OBJECTS and job is not None:
            try:
                win32api.CloseHandle(job)
                job = None
            except Exception:
                pass

        try:
            if proc.poll() is None:
                proc.kill()
                try: proc.wait(timeout=2)
                except Exception: pass
        except Exception:
            pass

        if out_path.exists() and out_path.stat().st_size > 1000:
            return idx, True
    except Exception as e:
        with open(LOG, 'a') as f:
            f.write(f'  ex {idx}: {type(e).__name__}: {str(e)[:100]}\n')
        if job is not None:
            try: win32api.CloseHandle(job)
            except Exception: pass
            job = None
    finally:
        if HAVE_JOB_OBJECTS and job is not None:
            try: win32api.CloseHandle(job)
            except Exception: pass
    return idx, False


def main():
    log('=== ffmpeg poster extractor (job-object timeout) ===')

    hls_cams = []
    with open(CSV_PATH, encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get('type') == 'hls' and r.get('live_stream_url') and r.get('idx', '').isdigit():
                hls_cams.append((r['idx'], r['live_stream_url']))
    log(f'Found {len(hls_cams)} HLS cams')

    # Always rebuild from disk to be the source of truth (this script may
    # restart many times; the progress file might be stale from a crash).
    on_disk = set()
    for f in OUT_DIR.iterdir():
        if f.is_file() and f.stat().st_size > 1000:
            on_disk.add(f.stem)
    done_set = on_disk
    failed_set = set()
    log(f'On disk: {len(done_set)} posters')

    to_do_raw = [(idx, url) for idx, url in hls_cams if idx not in done_set and idx not in failed_set]
    log(f'To process (pre-filter): {len(to_do_raw)}')

    if not to_do_raw:
        log('All done')
        # Write the full done list so progress file is in sync
        with open(PROGRESS, 'w', encoding='utf-8') as f:
            json.dump({'done': sorted(done_set, key=int), 'failed': []}, f)
        return

    # Pre-filter: skip URLs we know are slow or non-HTTP
    filtered = []
    failed_filtered_idxs = []
    for idx, url in to_do_raw:
        if not url or not url.startswith(('http://', 'https://')):
            failed_filtered_idxs.append(idx)
            continue
        if 'rtmp://' in url or 'rtsp://' in url.lower():
            failed_filtered_idxs.append(idx)
            continue
        filtered.append((idx, url))
    to_do = filtered
    log(f'After filter: {len(to_do)} to process ({len(failed_filtered_idxs)} filtered out)')

    if not to_do:
        log('Nothing to do')
        return

    # Write initial progress file with all known done cams (sorted ints)
    initial_progress = {'done': sorted(done_set, key=int), 'failed': failed_filtered_idxs[:]}
    with open(PROGRESS, 'w', encoding='utf-8') as f:
        json.dump(initial_progress, f)

    t0 = time.time()
    succeeded = 0
    failed = 0
    processed = 0
    success_lock_path = PROGRESS.with_suffix('.lock')

    def record_result(idx, ok):
        """Append result to progress file with file locking for thread safety."""
        import msvcrt
        # Retry loop to acquire lock
        for _ in range(50):
            try:
                # Create lock file exclusively
                fd = os.open(str(success_lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
                os.close(fd)
                break
            except FileExistsError:
                time.sleep(0.05)
        else:
            return  # couldn't lock, skip
        try:
            try:
                with open(PROGRESS, encoding='utf-8') as f:
                    p = json.load(f)
            except Exception:
                p = {'done': list(done_set), 'failed': []}
            if ok:
                p['done'].append(idx)
            else:
                p['failed'].append(idx)
            # Atomic write: write to temp file then rename
            tmp = PROGRESS.with_suffix('.tmp')
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(p, f)
            os.replace(tmp, PROGRESS)
        finally:
            try: os.unlink(str(success_lock_path))
            except Exception: pass

    with ThreadPoolExecutor(max_workers=12) as ex:
        futures = [ex.submit(extract_frame, idx, url) for idx, url in to_do]
        log(f'  Submitted {len(futures)} futures, awaiting first...', flush=True)
        for fut in as_completed(futures):
            try:
                idx, ok = fut.result()
            except Exception as e:
                ok = False
                idx = '?'
                log(f'  err: {e}')
            processed += 1
            if ok:
                succeeded += 1
            else:
                failed += 1
            record_result(idx, ok)
            if processed % 25 == 0 or processed == len(to_do) or processed == 1 or processed == 5:
                elapsed = time.time() - t0
                rate = processed / elapsed if elapsed > 0 else 0
                eta = (len(to_do) - processed) / rate if rate > 0 else 0
                log(f'  {processed}/{len(to_do)} ({succeeded} ok, {failed} fail), {rate:.1f}/s, eta {eta/60:.0f}min', flush=True)

    elapsed = time.time() - t0
    log(f'\nDone. {succeeded} succeeded, {failed} failed, in {elapsed/60:.1f} min')


if __name__ == '__main__':
    main()
