import csv, json
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv', 'r', encoding='utf-8', newline='') as f:
    rows = list(csv.reader(f))
with open(r'C:\Users\eli6-admin\Documents\eli6-surveillance\backups\cam_bruteforce_results.json', 'r') as f:
    cache = json.load(f)
hits = [k for k, v in cache.items() if v.get('http_creds') or v.get('cves') or v.get('rtsp_unauth') or v.get('rtsp_creds')]
print(f'cache: {len(cache)} ips')
print(f'hits so far: {len(hits)}')
http_hits = sum(1 for v in cache.values() if v.get('http_creds'))
cve_hits = sum(1 for v in cache.values() if v.get('cves'))
rtsp_unauth = sum(1 for v in cache.values() if v.get('rtsp_unauth'))
rtsp_creds = sum(1 for v in cache.values() if v.get('rtsp_creds'))
print(f'  http_creds: {http_hits}')
print(f'  cves: {cve_hits}')
print(f'  rtsp_unauth: {rtsp_unauth}')
print(f'  rtsp_creds: {rtsp_creds}')
auth_required = sum(1 for r in rows[1:] if len(r) > 5 and r[5] == 'yes')
bf_notes = sum(1 for r in rows[1:] if len(r) > 33 and 'bf:' in r[33])
print()
print(f'CSV rows with auth_required=yes: {auth_required}')
print(f'CSV rows with bf: in notes: {bf_notes}')
