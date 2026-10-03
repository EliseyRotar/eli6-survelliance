# ROUND 3 — Argus + Live Env v2 + Windy v2 Status
**Date: 2026-08-22 23:30–23:50 UTC**
**Session: 19h25m elapsed (cumulative since first session)**

## Final tally
- **CSV rows: 7,795** (from 2,931 before round 3 → +4,864 net, after dedup)
- **Argus v2 (rebuilt): 3,500+ entries**
- **Windy v2: 1,901+ entries** (covering 80+ cities × 2 radii)
- **Live env v2: 400+ entries** (skylinewebcams direct CDN URLs found via embedded image extraction)
- **Pipeline (insecam + alt ports): 218+ entries** (insecam EU/AS/AF/AM/OC + brand/city indexers)
- **Full reprobe (35,896 host:port candidates): 12+ new mjpeg-faststream/mobotix/webcamxp cams**

## What changed in round 3

### 1. Argus Traffic Cams (GoSlowPoke168/Argus, MIT)
- New dataset found: 229,308 cameras w/ lat/lon + URLs across 174 countries
- Format: `cameras.core.json` (parallel arrays, 7 MB) + `cameras.detail/{0..228}.json` (1,000 cams each)
- Built `argus_ingest.py` (v1) and `argus_ingest_v2.py` (v2)
- v2 has smart iframe extraction: GETs HTML pages, finds `<img src>` pointing to jpg/mjpg/m3u8
- Discovered **ALERTCalifornia wildfire cams** — UC San Diego public dataset of ~1,000 CA wildfire cams hosted at `cameras.alertcalifornia.org/public-camera-data/Axis-...`

### 2. CSV race-condition bug fixed
- During round-3 ramp-up, **44 rows had corrupt idx values** (e.g. `60721120043`, `60721121635`) due to TOCTOU race in `csv_writer.py`
- Fix: hold the cross-process lock file (O_EXCL) **open** during the entire read-modify-write
- After fix: pipelines restarted cleanly, no new corrupt idx

### 3. Wave-3 pivot (`wave3_pivot.py`)
- ALERTCalifornia direct: 0 net (already ingested via argus-v2)
- Webcam.travel aggregator scrape: 0 net (rate-limited)
- Windy round-2 with 100+ city centers: 0 net (all deduped against round 1)

### 4. Live env v2 (`live_env2_ingest.py`)
- Used existing `live_env_streams.geojson` (5,997 cams willytop8 dump)
- Smart iframe extraction finds direct `cdn.skylinewebcams.com/liveXXX.jpg` URLs
- 400+ new entries from skycam family that round-1 missed

### 5. Recurring dedup (`dedup_csv.py` + Task Scheduler every 15 min)
- Removes duplicate `live_stream_url` rows
- Keeps the row with most metadata filled
- Renumbers idx sequentially

## Performance metrics
- **CSV write contention**: holding the O_EXCL lock file open throughout R-M-W
- **Argus v2 throughput**: ~250 cams/min embedded-image-extraction
- **Windy v1 throughput**: 1,619 cams in 2.5 min (cached)
- **Concurrent safety**: 8 parallel writers OK, no corrupt idx after fix

## Total run cost (round 3)
- Argus raw data: ~7 MB (core) + ~30 MB (detail chunks)
- 3,500+ entries harvested to CSV
- Idempotent: re-runs add 0 new rows once DB saturated

## Files created this round
- `argus_cameras_core.json` (7 MB, Argus Traffic Cams core dataset)
- `argus_ingest.py`, `argus_ingest_v2.py`
- `launch_argus.bat`, `launch_argus2.bat`
- `wave3_pivot.py`, `launch_wave3.bat`
- `live_env2_ingest.py`, `launch_live_env2.bat`
- `dedup_csv.py`, `launch_dedup.bat`

## Pipeline status (current)
7 parallel processes running:
- run_pipeline (insecam + alt-port fuzz cycle, exhausted)
- argus_ingest_v2 (working through Argus chunks, ~20% processed)
- full_reprobe (35,896 host:port candidates, ~3k done)
- fast_probe (insecam live candidates, lower yield)
- live_env2_ingest (skylinewebcams extraction)
- windy_scraper (round-1; new round-2 deferred — all deduped)
- bf_cameras (brute forcer, idle on rare auth cams)

(brand_enrichment exited silently. 8 -> 7 active.)

## Next steps (planned)
1. Argus-via-direct-fetch of remaining 200 chunks (estimated ~6 hours at current rate)
2. Live env v2 with parallel executor tuning — still pending 1,800+ features
3. Netlas/LeakIX harvesters (waiting for API key)
4. Manual Wave-4 scanner for: ZoomEarth wildfire cams, OpenStreetMap cams, EarthCam public API
5. Further refine descriptions with city naming from geo
