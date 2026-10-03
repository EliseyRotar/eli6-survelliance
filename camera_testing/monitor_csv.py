import csv, os, time
path = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
prev = -1
for i in range(8):
    try:
        with open(path, 'r', encoding='utf-8', newline='') as f:
            rows = list(csv.reader(f))
        size = os.path.getsize(path)
        mx = max((int(r[0]) for r in rows[1:] if r[0].isdigit()), default=0)
        print(f'{time.strftime("%H:%M:%S")} size={size} rows={len(rows)} max_idx={mx}')
    except PermissionError as e:
        print(f'{time.strftime("%H:%M:%S")} LOCKED: {e}')
    time.sleep(8)
