import sys
sys.path.insert(0, r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing')
import probe_lib
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import requests, time, importlib.util

spec = importlib.util.spec_from_file_location('run_pipeline', r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\run_pipeline.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

s = requests.Session()
retries = Retry(total=0, backoff_factor=0.0, status_forcelist=[])
s.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20))
s.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20))
s.headers.update({'User-Agent': 'curl/8.4.0', 'Accept': '*/*'})

# 3 cams from earlier insecam round
cams = [
    ('109.164.108.99', 80, False),
    ('217.12.54.147', 8080, False),
    ('85.163.238.34', 80, False),
]
t0 = time.time()
for host, port, ssl in cams:
    print(f'probing {host}:{port}...')
    r = mod.probe_one(s, host, port, ssl, 3.0)
    print(host, port, '->', r)
print('total', time.time() - t0)
