"""Dead cam reaper - probes all cam URLs and removes dead ones.

Two modes:
- 'probe': quickly probe all URLs, return stats
- 'reap': probe + remove dead rows from CSV

The reaper identifies dead cams as:
- HTTP status >= 400 (except 401/403/407/451 which are auth-blocked)
- Connection errors
- Timeouts
"""
import csv
import os
import sys
import time
import re
import json
import random
import urllib.request
import ssl
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

sys.stdout.reconfigure(line_buffering=True)

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
DB_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\webcams.db'

# Auth-blocked codes (don't count as dead)
AUTH_CODES = {401, 403, 407, 451}

# Content types considered "live image"
IMAGE_CT = {'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp',
            'multipart/x-mixed-replace', 'application/octet-stream'}
VIDEO_CT = {'video/mp4', 'application/vnd.apple.mpegurl', 'video/x-m4v',
            'application/x-mpegurl', 'video/quicktime', 'video/webm'}

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def probe(url, timeout=5, max_bytes=2048):
    """Probe a single URL. Returns (status_code, content_type, size, latency_ms)."""
    try:
        t0 = time.time()
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64) AppleWebKit/537.36',
            'Accept': '*/*',
        })
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            data = r.read(max_bytes)
            latency = (time.time() - t0) * 1000
            return (r.status, r.headers.get('Content-Type', ''), len(data), latency)
    except urllib.error.HTTPError as e:
        return (e.code, '', 0, 0)
    except Exception as e:
        return (-1, str(e)[:50], 0, 0)


def is_dead(status, ct, size, url):
    """Determine if a cam is dead."""
    # divas.cloud / fl511 HLS URLs: 401/403/429/500/503 = token expired, NOT cam dead
    # (tokens rotate every ~5min; cam itself is fine, just need fresh token)
    if isinstance(url, str) and ('divas.cloud' in url or 'fl511.com' in url):
        if status in (401, 403, 429) or (500 <= status < 600):
            return False
        # Connection errors on divas often = network/CDN glitch, not cam death
        if status < 0:
            return False
    # Auth-required = not dead, just needs creds
    if status in AUTH_CODES:
        return False
    # Connection errors = dead
    if status < 0:
        return True
    # Server errors
    if status >= 500:
        return True
    # Client errors (404, 410)
    if status in (404, 410, 451):
        return True
    # Empty response
    if size < 100:
        return True
    # OK status
    if status == 200:
        return False
    return True


def main():
    # PID-based lock to prevent multiple reapers
    pid_file = r'C:\Users\eli6-admin\Documents\eli6-surveillance\cam_reaper.pid'
    my_pid = os.getpid()
    if os.path.exists(pid_file):
        try:
            with open(pid_file) as f:
                old_pid = int(f.read().strip())
            if old_pid != my_pid:
                # Check if still running
                try:
                    import psutil
                    if psutil.pid_exists(old_pid):
                        proc = psutil.Process(old_pid)
                        cmd = ' '.join(proc.cmdline() or [])
                        if 'cam_reaper' in cmd:
                            print(f'[Reaper] Already running as PID {old_pid}, exiting', flush=True)
                            return
                except ImportError:
                    pass
                except Exception:
                    pass
        except Exception:
            pass
    with open(pid_file, 'w') as f:
        f.write(str(my_pid))

    csv.field_size_limit(2**31 - 1)

    # Load CSV
    print(f'[Reaper] Loading {CSV_PATH}...', flush=True)
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace', newline='') as f:
        rows = list(csv.DictReader(f))
    print(f'  {len(rows):,} rows loaded', flush=True)

    # Get all URLs (skip empty)
    urls_to_probe = []
    for i, row in enumerate(rows):
        url = row.get('url', '') or ''
        lsurl = row.get('live_stream_url', '') or ''
        # Prefer live_stream_url if different
        if lsurl and lsurl != url and not lsurl.startswith('https://fl511.com:443'):
            target = lsurl
        else:
            target = url
        if target and not target.startswith('https://fl511.com:443'):  # skip generic host
            urls_to_probe.append((i, target, row.get('type', '') or '', row.get('live_status', '') or ''))

    print(f'  {len(urls_to_probe):,} URLs to probe', flush=True)

    # Probe all
    print(f'\n[Probing] Starting parallel probe...', flush=True)
    results = {}
    results_lock = threading.Lock()
    # Load existing results
    if os.path.exists('reap_results.json'):
        try:
            with open('reap_results.json') as f:
                existing = json.load(f)
            for k, v in existing.items():
                results[int(k)] = tuple(v)
            print(f'  Resumed with {len(results):,} existing results', flush=True)
        except Exception as e:
            print(f'  Resume err: {e}', flush=True)

    # Loop forever to keep reaping new cams and re-checking dead ones
    cycle = 0
    while True:
        cycle += 1
        pending = [(i, u, _, _) for i, u, _, _ in urls_to_probe if i not in results]
        # Re-probe a sample of dead cams each cycle (random 5%)
        to_reprobe = []
        if cycle >= 2:
            dead_ids = []
            for i, u, _, _ in urls_to_probe:
                if i in results:
                    r = results[i]
                    status = r[0]
                    if status not in (200, 401, 403, 407, 451):
                        dead_ids.append((i, u, _, _))
            # Sample 5% of dead
            n_reprobe = max(1, len(dead_ids) // 20)
            to_reprobe = random.sample(dead_ids, n_reprobe)
            # Add to pending
            pending.extend(to_reprobe)
            # Remove from results so they get re-probed (and re-saved)
            for i, u, _, _ in to_reprobe:
                results.pop(i, None)

        if not pending:
            print(f'  [Cycle {cycle}] Nothing to do, sleeping 2min...', flush=True)
            time.sleep(120)
            continue

        print(f'  [Cycle {cycle}] {len(pending):,} URLs to probe ({len(to_reprobe):,} re-probes)', flush=True)

        t0 = time.time()
        n_done = 0
        n_alive = 0
        n_dead = 0
        n_auth = 0
        n_err = 0
        save_every = 500

        with ThreadPoolExecutor(max_workers=50) as ex:
            futs = {ex.submit(probe, u): (i, u) for i, u, _, _ in pending}
            for f in as_completed(futs):
                idx, url = futs[f]
                try:
                    status, ct, size, latency = f.result(timeout=8)
                    with results_lock:
                        results[idx] = (status, ct, size, latency, url)
                    if status in AUTH_CODES:
                        n_auth += 1
                    elif is_dead(status, ct, size, url):
                        n_dead += 1
                    else:
                        n_alive += 1
                    if status < 0:
                        n_err += 1
                except Exception as e:
                    with results_lock:
                        results[idx] = (-1, str(e)[:50], 0, 0, url)
                    n_dead += 1
                    n_err += 1
                n_done += 1
                if n_done % 1000 == 0:
                    elapsed = time.time() - t0
                    rate = n_done / max(elapsed, 1)
                    print(f'  {n_done:,}/{len(pending):,} ({rate:.0f}/s) alive={n_alive:,} dead={n_dead:,} auth={n_auth:,} err={n_err:,}', flush=True)
                if n_done % save_every == 0:
                    tmp_path = 'reap_results.json.tmp'
                    with results_lock:
                        snapshot = {str(k): list(v) for k, v in results.items()}
                    with open(tmp_path, 'w') as f:
                        json.dump(snapshot, f)
                    try:
                        os.replace(tmp_path, 'reap_results.json')
                    except OSError:
                        pass

        elapsed = time.time() - t0
        rate = len(pending) / max(elapsed, 1)
        print(f'\n[Cycle {cycle} Done] {len(pending):,} probed in {elapsed:.0f}s ({rate:.0f}/s)', flush=True)
        print(f'  Total in results: {len(results):,}', flush=True)
        print(f'  This cycle: alive={n_alive:,} dead={n_dead:,} auth={n_auth:,} err={n_err:,}', flush=True)

        # Save final results for this cycle
        with results_lock:
            snapshot = {str(k): list(v) for k, v in results.items()}
        with open('reap_results.json', 'w') as f:
            json.dump(snapshot, f)
        print(f'  Saved final results for cycle {cycle}', flush=True)

    elapsed = time.time() - t0
    rate = len(pending) / max(elapsed, 1)
    print(f'\n[Cycle {cycle} Done] {len(pending):,} probed in {elapsed:.0f}s ({rate:.0f}/s)', flush=True)
    print(f'  Total in results: {len(results):,}', flush=True)
    print(f'  This cycle: alive={n_alive:,} dead={n_dead:,} auth={n_auth:,} err={n_err:,}', flush=True)

    # Save final results for this cycle
    with results_lock:
        snapshot = {str(k): list(v) for k, v in results.items()}
    with open('reap_results.json', 'w') as f:
        json.dump(snapshot, f)
    print(f'  Saved final results for cycle {cycle}', flush=True)

    # Status code histogram
    sc = Counter()
    for status, ct, size, latency, url in results.values():
        sc[status] += 1
    print(f'\nCycle {cycle} status histogram:')
    for code, count in sc.most_common(15):
        print(f'  {code}: {count:,}')


if __name__ == '__main__':
    main()
