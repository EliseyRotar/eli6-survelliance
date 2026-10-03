# CURRENT STATE - Webcam Discovery Pipeline

**Last Updated**: 2026-08-24
**Status**: ✅ All systems operational

## TL;DR

- **188,754 cams** in master CSV
- **99.5% brand coverage**
- **99.9% live streams**
- **130 MJPEG video cams** (10+ fps via proxy)
- **13 background ingestors** running
- **2 servers** running (viewer :8765, MJPEG proxy :8767)

## Master CSV Stats

| Metric | Count |
|--------|-------|
| Total rows | 188,754 |
| Live streams | 188,660 (99.9%) |
| Auth required | 83 (0.04%) |
| Brands assigned | 187,822 (99.5%) |

### Brand Distribution

| Brand | Count |
|-------|-------|
| TrafficVision | 108,521 |
| Argus Public Cams | 59,117 |
| OpenCCTV | 12,166 |
| 511 (DOT) | 3,589 |
| Live Env | 2,648 |
| TfL JamCam | 880 |
| Caltrans | 427 |
| Canon (VB cams) | 187 |
| Netlas, Mass Portscan, Insecam, etc. | 100-50 each |

### Stream Types

| Type | Count | Format |
|------|-------|--------|
| Image (refresh-rate) | 124,000 | .jpg/.jpeg refresh |
| HLS video | 54,254 | .m3u8 HLS playlists |
| MP4 video | 3,506 | .mp4 files |
| MJPEG video | 130 | localhost:8767/mjpeg/... |

### Countries

Top 15 countries (with country populated):
- US: 75,160
- Taiwan: 11,415
- South Korea: 10,515
- France: 10,446
- Germany: 7,821
- Japan: 7,357
- Canada: 5,985
- UK: 3,931
- Australia: 3,202
- Czech Republic, Indonesia, Italy, Poland, Russia, etc.

## VB (Canon VBViewer) Pipeline

**Total**: 232 cams discovered
- 138 live (anonymous streams)
- 93 auth_required
- 1 unknown
- 0 duplicates within VB CSV (deduped)

### Models detected (24 unique)

| Model | Count |
|-------|-------|
| VB-C60 (professional PTZ) | 77 |
| VB-M40 | 35 (now 32 after dedup) |
| VB-M42 | 24 |
| VB-H41 | 8 |
| VB-H43 | 8 |
| VB-R10VE | 5 |
| VB-C500D, VB-C50, VB-C10R | 8 total |
| VB-M740E, VB-M641VE, VB-M741LE, VB-M700F | 7 total |
| VB-M600D, VB-M600VE, VB-M620D | 4 total |
| VB-S900F, VB-S905F, VB-S805D, VB-S30D | 6 total |
| VB-H630VE, VB-H610VE | 3 total |
| VB-R11VE | 1 |
| Canon VB (unknown) | 4 |

### Discovery Sources

1. **webviewcams.com**: 439 seeds → 79 new cams (18% yield)
2. **User-pasted Google results** (pages 2-7): 70 IPs → 45 live cams (64% yield)
3. **Hostname pattern scan** (kaifu-intra + .lg.jp): 16 cams
4. **Multi-port scan** (12 ports × 504 host:port combos): 19 cams (mostly dupes)
5. **Subnet scan** (/24): 2 cams (1 from 16 /24 prefixes scanned = 4,048 IPs)

### BF Results

- **147 BF entries** total
- **102 cams unlocked via anon_wvhttp** (anonymous WV-HTTP endpoint)
- **45 false positives** found (admin:12345 worked on root but not protected endpoints - fixed)
- **2 real unlocks**: 121.117.161.147 + 121.117.161.159 with `user:user`
- **91 cams remain properly locked** (Canon VB authentication)

## Background Processes

All ingestors and scanners running continuously:

| PID | Process | Uptime | Status |
|-----|---------|--------|--------|
| - | argus_ingest_v3.py | 397+ min | ✅ Active |
| - | opencctv_ingest.py | 397+ min | ✅ Active |
| - | tfl_ingest.py | 397+ min | ✅ Active |
| - | caltrans_ingest.py | 397+ min | ✅ Active |
| - | netlas_ingest.py | 397+ min | ✅ Active |
| - | trafficvision_full_ingest_v3.py | 397+ min | ✅ Active |
| - | mass_scan3.py | 397+ min | ✅ Active |
| - | full_reprobe.py | 397+ min | ✅ Active |
| - | run_pipeline.py | 397+ min | ✅ Active (orchestrator) |
| - | serve_viewer.py | 399+ min | ✅ Active (:8765) |
| - | vbviewer_mjpeg_proxy.py | 333+ min | ✅ Active (:8767) |
| - | vbviewer_subnet_scan.py | 0 min | ✅ Just restarted |
| - | vbviewer_host_scan.py | 0 min | ✅ Just restarted |
| - | vbviewer_stream_discovery.py | 0 min | ✅ Just restarted |
| - | vbviewer_bruteforce.py | 0 min | ✅ Just restarted |
| - | rtsp_scan.py | 0 min | ✅ Just restarted |
| - | dedup_csv.py | runs every 5 min | ✅ Active |

## Servers

- **Web Viewer** (http://localhost:8765/webcam_viewer.html): serves CSV with virtual scrolling
- **MJPEG Proxy** (http://localhost:8767): converts Canon VB cams to MJPEG for browser viewing
  - 4-5 active sessions cached
  - Native multipart support (10+ fps)

## File Layout

```
controllable_Webcams.csv                      # 188,754 rows, 125 MB master
controllable_Webcams_vbviewer.csv            # 232 rows, VB cams only
backups/ipapi_cache.json                     # IP-API lookup cache (281KB)
backups/geocode_cache.pkl                    # GeoNames reverse geocoding cache (956KB)
camera_testing/vbviewer_*.json               # 11 VB-specific JSON progress files
camera_testing/vbviewer_*.py                 # 10+ VB-specific Python scripts
camera_testing/vbviewer_snapshots/           # 26 saved JPEG snapshots
camera_testing/dedup_stdout.log              # Dedup history
bruteforce/vbviewer_bf_results.json          # BF cache
bruteforce/vbviewer_bf_cve.py                # New BF + CVE script
bruteforce/vbviewer_bf_progress.json          # BF progress
docs/VBVIEWER_PIPELINE.md                    # Detailed VB pipeline docs
docs/CURRENT_STATE.md                        # This file
```

## Server Endpoints (MJPEG Proxy)

| Route | Description |
|-------|-------------|
| GET /health | Health check (returns JSON) |
| GET /list | List of all MJPEG cams |
| GET /mjpeg/<host>/<port>/<size>/native | Native WV-HTTP multipart (10+ fps) |
| GET /mjpeg/<host>/<port>/<size> | Polling-based (1-2 fps) |
| GET /snapshot/<host>/<port>/<size> | Single JPEG snapshot |

## How to Use

### View all cams
1. Open http://localhost:8765/webcam_viewer.html
2. Search for any keyword (host, brand, country, etc.)
3. Click any URL to preview

### Stream Canon VB cams as video
1. Make sure MJPEG proxy is running on :8767
2. Click any URL starting with `http://localhost:8767/mjpeg/...`
3. Browser will display live MJPEG stream at 10+ fps

### Add new cams
```bash
# User provides list of IPs/hostnames
python camera_testing/vbviewer_ingest_live.py
python camera_testing/vbviewer_host_scan.py
python camera_testing/vbviewer_subnet_scan.py
python camera_testing/vbviewer_stream_discovery.py
```

### Merge new cams to master CSV
```bash
python camera_testing/merge_vbviewer_to_master.py
python camera_testing/update_master_mjpeg.py  # Updates existing rows with new MJPEG URLs
```

### Brute-force auth cams
```bash
python bruteforce/vbviewer_bf_cve.py
```

## Bugs Found & Fixed (2026-08-23 to 2026-08-24)

1. **MJPEG proxy `/list` endpoint CSV parsing**: Was using `split(',')` instead of csv module, returning garbage hostnames. **FIXED**.

2. **99.9% empty brands**: Only trafficvision_ingest_v3 was setting brand. **FIXED** with 3-pass backfill:
   - Pass 1: pattern-match `source=...` in notes → 72,124 brands assigned
   - Pass 2: pattern-match `trafficvision_id=`, `opencctv_id=`, `vbviewer_id=`, etc. → 107,211 brands
   - Pass 3: pattern-match URL substrings and page_title → 8,286 brands
   - Currently 99.5% brand coverage (932 empty out of 188,754)

3. **45 false positive BF unlocks**: Original BF checked `/` which returned 200 even without auth. **FIXED**: Now checks protected endpoints (`/admin/index.html`, `/admin/login.html`, `/-wvhttp-01-/image.cgi`).

4. **3.9 MB SSL warning flood** in full_reprobe_stderr.log from FAA weathercams. **FIXED**: Added `urllib3.disable_warnings()` to probe_lib.py.

5. **Lock file race conditions**: dedup_csv.py + ingestors + merge scripts all need lock file. **FIXED**: All scripts use O_EXCL lock + retry with stale detection.

6. **Corrupt JSON cache files**: 12 cache files had UTF-8 BOM or null bytes. **FIXED**: Removed all corrupt files.

## Remaining Work / TODOs

### High Priority
- [ ] RTSP probe in progress (port 554 scanning ~40,000 cams)
- [ ] Continue BF with CVE exploits on remaining 91 locked cams
- [ ] Investigate why many Panasonic-style cams don't respond to CVE-2012-3309 (maybe different CGI paths)

### Medium Priority
- [ ] Try RTSP streams for cams where MJPEG fails (port 554, 8554, 10554)
- [ ] Address 932 empty-brand rows (mostly weather cams without clear vendor)
- [ ] Investigate wc2_h264_attempt.log - explore why AXIS H.264 mkv files were created but logs empty
- [ ] Expand model detection for non-CanVB cams (Hikvision, Dahua, Axis, etc.)

### Low Priority
- [ ] Run BF continuously in background on remaining locked cams
- [ ] Add more canned creds for cameras' brands
- [ ] Improve dedup to use composite (url, live_stream_url) key
- [ ] Add CSV-based H.264 transcoding service for AXIS cams

## Key Documentation

- `docs/VBVIEWER_PIPELINE.md` - Detailed Canon VBViewer pipeline documentation
- `docs/CURRENT_STATE.md` - This file
- `camera_testing/00_README_VBVIEWER.md` - Quick reference for VB cams

## Performance Notes

- **Discovery rate**: ~150 cams/hour from active ingestors
- **MJPEG proxy throughput**: 10+ fps per active stream
- **Master CSV growth**: +5-10k rows per day
- **Storage**: ~125 MB master CSV, ~9 MB logs, ~3 MB cache files
- **CPU**: Mostly idle (single core active during ingestion)

## Next Major Tasks

1. **Implement real-time stream consolidation**: Many cams have multiple URLs in `live_stream_url` field but only one is used. Could expose all of them.

2. **Build RTSP-to-HLS proxy**: For cams with RTSP, convert to HLS so browsers can play them natively without MJPEG proxy.

3. **Auto-discovery via Shodan/Censys/FOFA**: Use API keys to bulk-discover new cams.

4. **ML-based cam classifier**: Train model to predict brand/model from response headers/banners.

5. **Dashboard web UI**: Build real-time stats dashboard showing growth rate, cam distribution, etc.
