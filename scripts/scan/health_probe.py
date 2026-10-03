"""Sample 50 random cameras from CSV and HEAD-probe each to verify they're still alive."""
import csv
import random
import urllib.request
import urllib.error
import socket
import threading
import time

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'

def head_url(url, timeout=5):
    """HEAD-probe URL. Returns (status_code, content_type, content_length) or (err, err, err)."""
    try:
        req = urllib.request.Request(url, method='HEAD')
        req.add_header('User-Agent', 'Mozilla/5.0')
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.headers.get('Content-Type', ''), r.headers.get('Content-Length', '?')
    except urllib.error.HTTPError as e:
        return e.code, '', '?'
    except (urllib.error.URLError, socket.timeout, ConnectionResetError) as e:
        return 'ERR', str(e)[:40], '?'

with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
    rows = list(csv.reader(f))

print(f'total rows: {len(rows)-1}')

# Diverse sample: 50 random URLs from various sources
random.seed(123)
sample_size = 50
sample_idxs = random.sample(range(1, len(rows)), min(sample_size, len(rows)-1))

results = {'200': 0, '301': 0, '302': 0, '401': 0, '403': 0, '404': 0, '500': 0, 'timeout': 0, 'err': 0, 'other': 0}
results_img = 0  # confirmed image/video content
results_alive = 0  # 2xx or 401 (cam might be there but needs auth)

print(f'\nProbing {len(sample_idxs)} random cameras...')
t0 = time.time()
for idx in sample_idxs:
    r = rows[idx]
    url = r[3] if len(r) > 3 else ''
    if not url:
        continue
    status, ct, cl = head_url(url, timeout=4)
    if isinstance(status, int):
        if status == 200: results['200'] += 1; results_alive += 1
        elif status == 301: results['301'] += 1; results_alive += 1
        elif status == 302: results['302'] += 1; results_alive += 1
        elif status == 401: results['401'] += 1; results_alive += 1
        elif status == 403: results['403'] += 1
        elif status == 404: results['404'] += 1
        elif status == 500: results['500'] += 1
        else: results['other'] += 1
        if 'image' in ct.lower() or 'multipart' in ct.lower() or 'video' in ct.lower() or 'octet' in ct.lower():
            results_img += 1
    else:
        if 'timeout' in str(status).lower():
            results['timeout'] += 1
        else:
            results['err'] += 1
elapsed = time.time() - t0

print(f'\nResults ({elapsed:.1f}s for {len(sample_idxs)} probes):')
for k, v in results.items():
    if v > 0:
        print(f'  {k}: {v}')
print(f'  ---')
print(f'  alive (2xx/3xx/401): {results_alive}')
print(f'  confirmed image/video content-type: {results_img}')
print(f'  alive rate: {results_alive*100/len(sample_idxs):.1f}%')
