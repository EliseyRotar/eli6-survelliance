"""Extract encrypted streams from a ZipCrypto ZIP for bkcrack known-plaintext attack."""
import struct
import os

zip_path = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\nolandda_ssh-dir.zip'
out_dir = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\bkcrack_work'

os.makedirs(out_dir, exist_ok=True)

with open(zip_path, 'rb') as f:
    data = f.read()

eocd_offset = data.rfind(b'PK\x05\x06')
eocd = data[eocd_offset:eocd_offset+22]
cd_offset = struct.unpack('<I', eocd[16:20])[0]

entries = []
pos = cd_offset
while pos < eocd_offset:
    sig = data[pos:pos+4]
    if sig != b'PK\x01\x02':
        break
    name_len = struct.unpack('<H', data[pos+28:pos+30])[0]
    extra_len = struct.unpack('<H', data[pos+30:pos+32])[0]
    comment_len = struct.unpack('<H', data[pos+32:pos+34])[0]
    local_header_offset = struct.unpack('<I', data[pos+42:pos+46])[0]
    comp_size = struct.unpack('<I', data[pos+20:pos+24])[0]
    uncomp_size = struct.unpack('<I', data[pos+24:pos+28])[0]
    compression = struct.unpack('<H', data[pos+10:pos+12])[0]
    flag = struct.unpack('<H', data[pos+8:pos+10])[0]
    name = data[pos+46:pos+46+name_len].decode('utf-8', errors='replace')
    entries.append({
        'name': name,
        'local_offset': local_header_offset,
        'comp_size': comp_size,
        'uncomp_size': uncomp_size,
        'compression': compression,
        'flag': flag,
    })
    pos += 46 + name_len + extra_len + comment_len

print(f'Found {len(entries)} entries')
for e in entries:
    if not (e['flag'] & 1):
        continue
    lh = data[e['local_offset']:e['local_offset']+30]
    name_len = struct.unpack('<H', lh[26:28])[0]
    extra_len = struct.unpack('<H', lh[28:30])[0]
    data_start = e['local_offset'] + 30 + name_len + extra_len
    enc_data = data[data_start:data_start + e['comp_size']]
    safe = e['name'].replace('/', '_').replace('.', '_')
    out = os.path.join(out_dir, f'cipher_{safe}.bin')
    with open(out, 'wb') as fo:
        fo.write(enc_data)
    print(f"{e['name']:42}  uncomp={e['uncomp_size']:6}  comp={e['comp_size']:6}  enc_bytes={len(enc_data):6}  compress_method={e['compression']}")
    print(f'  -> {out}')

# Save plain.zip for bkcrack -C reference
import shutil
shutil.copy(zip_path, os.path.join(out_dir, 'nolandda_ssh-dir.zip'))

# Save known-plaintext file with the bytes we know
# id_ed25519_github.pub is 97 bytes; it starts with "ssh-ed25519 " (12 bytes) + base64 + comment
# We know the format: ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... user@host
# Actually let me save just the prefix we are SURE of
known = b'ssh-ed25519 '
plain_path = os.path.join(out_dir, 'plain.bin')
with open(plain_path, 'wb') as f:
    f.write(known)
print(f'Known plaintext ({len(known)} bytes): {known!r}')

# Try the bkcrack attack
import subprocess
bk = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\bkcrack\bkcrack-1.8.1-win64\bkcrack.exe'
zip_path = os.path.join(out_dir, 'nolandda_ssh-dir.zip')

# bkcrack args: -C cipher.zip -c cipherfilename -p plaintextfile
result = subprocess.run([bk, '-C', zip_path, '-c', 'ssh-dir/id_ed25519_github.pub', '-p', plain_path],
                       capture_output=True, text=True, timeout=600)
print(f'=== bkcrack exit code: {result.returncode} ===')
print('STDOUT:', result.stdout[-3000:] if result.stdout else '(empty)')
print('STDERR:', result.stderr[-3000:] if result.stderr else '(empty)')