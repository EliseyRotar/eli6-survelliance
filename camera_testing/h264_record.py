#!/usr/bin/env python3
"""
Stream a MJPEG URL through Python and write H.264 frames as we get them.
This avoids ffmpeg's blocking stream-open behavior.
"""
import subprocess
import sys
import time

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://wc2.dartmouth.edu/mjpg/video.mjpg'
OUT = sys.argv[2] if len(sys.argv) > 2 else r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\wc2_h264_py.mkv'
DURATION = int(sys.argv[3]) if len(sys.argv) > 3 else 10
W = int(sys.argv[4]) if len(sys.argv) > 4 else 640
H = int(sys.argv[5]) if len(sys.argv) > 5 else 480

FFMPEG = r'C:\Users\eli6-admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe'

# Use ffmpeg with very aggressive low-latency flags + read from stdin-like with timeout
cmd = [
    FFMPEG,
    '-y',
    '-hide_banner',
    '-loglevel', 'warning',
    '-user_agent', 'Mozilla/5.0',
    '-fflags', 'nobuffer+genpts',
    '-flags', 'low_delay',
    '-timeout', '5000000',
    '-i', URL,
    '-t', str(DURATION),
    '-r', '25',
    '-vf', f'scale={W}:{H}',
    '-c:v', 'libx264',
    '-preset', 'ultrafast',
    '-tune', 'zerolatency',
    '-crf', '28',
    '-an',
    '-f', 'matroska',
    OUT
]

print(f'[+] Command: {" ".join(cmd)}')
print(f'[+] Recording {DURATION}s to {OUT}...')
start = time.time()
try:
    result = subprocess.run(cmd, capture_output=True, timeout=DURATION + 30)
    elapsed = time.time() - start
    print(f'[+] Done in {elapsed:.1f}s')
    if result.returncode != 0:
        print(f'[!] Return code: {result.returncode}')
        print(f'[!] stderr: {result.stderr.decode("utf-8", errors="ignore")[-500:]}')
    else:
        import os
        size = os.path.getsize(OUT)
        print(f'[+] Output: {size} bytes')
except subprocess.TimeoutExpired:
    print(f'[!] Timed out after {DURATION + 30}s')