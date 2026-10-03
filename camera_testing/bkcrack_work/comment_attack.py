"""Test GitHub key with 15-char comments."""
import zlib
import os
import subprocess

key = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBopeRkclOrscs+rQVfK8bXmZ3ucAiJS2s2VVXWETWV0'

candidates = [
    'github.com/nolandda',  # 15
    'nolandda@github',     # 15
    'nolandda@ws-dc-01',   # 15
    'nolandda@ws-dc-02',   # 15
    'nolandda@dc-ws-01',   # 15
    'nolandda@t480s',       # 15
    'nolandda@laptop',      # 16 - skip
    'nolandda@m3800',       # 13 - skip
    'nolandda@m4800',       # 13 - skip
    'nolandda@m6800',       # 13 - skip
    'nolandda@latitude',    # 17 - skip
    'nolandda@optiplex',    # 18 - skip
    'nolandda@thinkpad',    # 18 - skip
    'nolandda@macbook',     # 17 - skip
    'nolandda@apollo',      # 16 - skip
    'nolandda@star lab',    # 17 - skip
    'nolandda@dc',          # 12 - skip
    'nolandda@home',        # 10 - skip
    'nolandda@kali',        # 11 - skip
    'nolandda@home-pc',     # 14 - skip
    'nolandda@xinu',        # 11 - skip
    'nolandda@nolan-pc01',  # 15
    'nolandda@ws.local',    # 15
    'nolandda@dc.local',    # 14 - skip
    'nolandda@ws-dc',       # 14 - skip
    'github@nolandda',      # 14 - skip
    'github-nolandda',      # 14 - skip
    'git@github.com:nola',  # 15
    'nolandda@dc-01',       # 13 - skip
    'nolandda@dc-1',        # 12 - skip
    'nolandda@dc-2',        # 12 - skip
    'nolandda@ws-dc-1',     # 14 - skip
    'nolandda@ws-dc-2',     # 14 - skip
    'nolandda@ws-dc-03',    # 15
    'nolandda@ws-dc-04',    # 15
    'nolandda@dc-1.local',  # 16 - skip
    'nolandda@dc-2.local',  # 16 - skip
    'nolandda@dc-1.lan',    # 15
    'nolandda@dc-2.lan',    # 15
    'nolandda@work-01',     # 15
    'nolandda@work-02',     # 15
    'nolandda@starlab.io',  # 18 - skip
    'nolandda@starlab',     # 16 - skip
    'nolandda@starship',    # 17 - skip
    'nolandda@localhost',   # 17 - skip
    'nolandda@nuc',          # 10 - skip
    'nolandda@home.lan',    # 15
    'nolandda@office.lan',  # 17 - skip
    'nolandda@work.lan',    # 15
    'nolandda@home.arpa',   # 16 - skip
    'nolandda@ws-dc-1.lan', # 17 - skip
    'github_nolandda',       # 14 - skip
    'github-nolandda-pc',   # 17 - skip
    'nolandda@home-pc',     # 14 - skip
    'nolandda@office',      # 16 - skip
    'nolandda@office-pc',   # 17 - skip
    'nolandda@star-pc',     # 15
    'nolandda@star-01',     # 15
    'nolandda@star-02',     # 15
    'nolandda@pc-nlan',     # 15
    'nolandda@dc-1.home',   # 16 - skip
    'nolandda@dc-2.home',   # 16 - skip
    'nolandda@ws-1.local',   # 17 - skip
    'nolandda@ws-2.local',   # 17 - skip
    'nolandda@ws-1.home',   # 16 - skip
    'nolandda@ws-2.home',   # 16 - skip
    'nolandda@ws-dc-1.home',# 18 - skip
    'nolandda@xps',         # 12 - skip
    'nolandda@xps-13',      # 14 - skip
    'nolandda@xps-15',      # 14 - skip
    'nolandda@xps-13-93',   # 17 - skip
    'nolandda@dc-1.local',  # 16 - skip
    'nolandda@dc-2.local',  # 16 - skip
    'nolandda@dc-3.local',  # 16 - skip
    'nolandda@dc-4.local',  # 16 - skip
    'nolandda@ws-1.local',  # 16 - skip
    'nolandda@ws-2.local',  # 16 - skip
    'nolandda@ws-3.local',  # 16 - skip
    'nolandda@ws-4.local',  # 16 - skip
    'nolandda@dc-3.lan',    # 15
    'nolandda@dc-4.lan',    # 15
    'nolandda@dc-5.lan',    # 15
    'nolandda@dc-6.lan',    # 15
    'nolandda@dc-7.lan',    # 15
    'nolandda@dc-8.lan',    # 15
    'nolandda@dc-9.lan',    # 15
    'nolandda@dc-a.lan',    # 15
    'nolandda@ws-3.home',   # 16 - skip
    'nolandda@ws-4.home',   # 16 - skip
    'nolandda@ws-5.home',   # 16 - skip
    'nolandda@ws-6.home',   # 16 - skip
    'nolandda@dc-3.home',   # 16 - skip
    'nolandda@dc-4.home',   # 16 - skip
]

# Filter to only 15-char comments
candidates = [c for c in candidates if len(c) == 15]

out_dir = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\bkcrack_work'
bk = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\bkcrack-src\bkcrack-1.8.1\build\src\bkcrack.exe'
zip_path = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\nolandda_ssh-dir.zip'

print(f'Testing {len(candidates)} 15-char comments at 4 compression levels = {len(candidates)*4} attacks')

# Generate compressed files and run bkcrack
for c in candidates:
    full = key + ' ' + c + '\n'
    assert len(full) == 97, f'Wrong size {len(full)} for {c!r}'
    for level in [6, 1, 4, 9]:
        comp = zlib.compressobj(level, zlib.DEFLATED, -15)
        comp_raw = comp.compress(full.encode()) + comp.flush()
        outpath = os.path.join(out_dir, f'plain_{c.replace("@", "_AT_")}_lv{level}.bin')
        with open(outpath, 'wb') as f:
            f.write(comp_raw)

print('Compressed plaintext candidates saved.')

# Run bkcrack
import glob
for plain_file in sorted(glob.glob(os.path.join(out_dir, 'plain_*_lv*.bin'))):
    result = subprocess.run(
        [bk, '-C', zip_path, '-c', 'ssh-dir/id_ed25519_github.pub', '-p', plain_file],
        capture_output=True, text=True, timeout=180
    )
    out = (result.stdout + result.stderr)
    if 'Keys:' in out:
        for line in out.splitlines():
            if line.startswith('Keys:'):
                print(f'*** FOUND: {line}')
                print(f'  Plain: {os.path.basename(plain_file)}')
                with open(os.path.join(out_dir, 'keys.txt'), 'w') as f:
                    f.write(line.split(':',1)[1].strip())
                break
        break
    else:
        pass  # No match
else:
    print('No match in any 15-char comment candidate')