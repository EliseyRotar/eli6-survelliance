# Webcam DB — Fast Query & Viewing Guide

The CSV has grown to **67,612 cams × 35 columns** (~50 MB). Loading it in Excel hangs. Here are faster ways:

## 1. Live Web Viewer (Best for browsing)

```cmd
launch_webcam_viewer.bat
```

Then open in your browser: **http://localhost:8765/webcam_viewer.html**

Features:
- Search by URL, host, country, city, ISP, brand
- Filter by type (MP4 / HLS .m3u8 / MJPEG / JPG)
- Filter by status (live / private)
- Click a row's URL to preview inline (MP4 native, HLS via hls.js)
- Click "▶ VLC" to copy URL to clipboard (paste into VLC)
- Click "↗" to open in new tab

## 2. SQLite Query Tool (Fast filtering)

```cmd
cd C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing

REM Show stats
python query_webcams.py --stats

REM Find all video MP4 cams in US
python query_webcams.py --format mp4 --country "United States" --limit 50

REM Find all .m3u8 (HLS) cams
python query_webcams.py --format m3u8 --limit 30

REM Find private cams in Italy
python query_webcams.py --private --country Italy --limit 30

REM Search for "Hikvision" or "Dahua" cams
python query_webcams.py --search Hikvision --limit 20

REM Find all cams from a specific IP
python query_webcams.py --host "62.96" --limit 10

REM Save results to CSV
python query_webcams.py --country "United States" --limit 1000 --out us_cams.csv
```

## 3. DB Browser for SQLite (GUI)

1. Download https://sqlitebrowser.org/dl/
2. Open `C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\webcams.db`
3. Browse the `webcams` table — it's much faster than CSV

## 4. Excel-compatible chunks (5k rows each)

CSV chunks in `C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\csv_chunks\`:
- `webcams_0000.csv` — first 5k cams
- `webcams_0001.csv` — next 5k
- ... up to `webcams_0013.csv`

Each opens in Excel without hanging.

## File sizes

- `controllable_Webcams.csv` — 50 MB, 67k rows
- `webcams.db` — 90 MB, queryable in <1 sec
- Per-row dump: `cam_<IP>/` folder for each IP with auth
