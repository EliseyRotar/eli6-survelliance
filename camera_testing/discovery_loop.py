"""Continuous cam-discovery orchestrator.

Cycles through all harvesters, deals with cross-process CSV lock contention,
and runs ~24/7.
"""
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
import harvest_lib
import probe_lib
import csv_writer


def session():
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    s = requests.Session()
    retries = Retry(total=0)
    s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=80, pool_maxsize=80))
    s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=80, pool_maxsize=80))
    s.headers.update({'User-Agent': 'Mozilla/5.0'})
    return s


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)


def run_script(script_name):
    """Run a Python script as a sub-process and tail output."""
    log(f'>>> launch {script_name}')
    py = r'C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\python.exe'
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    log_path = os.path.join(os.path.dirname(__file__), script_name.replace('.py', '_stdout.log'))
    p = subprocess.Popen([py, script_path], stdout=open(log_path, 'wb'), stderr=subprocess.STDOUT)
    log(f'    pid={p.pid}')
    return p


def run_blocking(script_name):
    """Run script and wait."""
    py = r'C:\Users\eli6-admin\AppData\Local\Programs\Python\Python312\python.exe'
    p = subprocess.run([py, os.path.join(os.path.dirname(__file__), script_name)], capture_output=True, text=True, timeout=300)
    return p.returncode


def main():
    log('=== continuous discovery orchestrator started ===')

    # Step 1: refresh insecam URLs
    log('phase 1: dump insecam URLs')
    run_blocking('camera_hack_dump.py')

    # Step 2: probe new URLs (live)
    log('phase 2: probe new URLs')
    p = run_script('fast_probe.py')
    # wait until done
    p.wait()

    # Step 3: insecam 2019 dump (stale cams check)
    log('phase 3: probe 2019 insecam dump')
    p = run_script('insecam_2019_ingest.py')
    p.wait()

    # Step 4: live_env streams (HLS)
    log('phase 4: live_env streams')
    run_blocking('live_env_ingest.py')

    log('all phases complete; sleeping 30 minutes...')
    time.sleep(1800)


if __name__ == '__main__':
    while True:
        try:
            main()
        except Exception as e:
            log(f'error: {e}')
            time.sleep(60)
