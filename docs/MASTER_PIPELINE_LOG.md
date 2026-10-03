# Master Pipeline Log

## Architecture

```
                                    MASTER CSV
                    /controllable_Webcams.csv (194k cams × 35 cols)
                          ↑
   ┌──────────────────────┼──────────────────────────┐
   │                      │                          │
   ▼                      ▼                          ▼
DISCOVERY              INGESTION                  STREAMING
- Shodan                - Argus (57k)              - MJPEG Proxy (:8767)
- InternetDB            - OpenCCTV (12k)           - RTSP Discovery
- insecam-v2            - TrafficVision (108k)     - H.264 Transcoding
- camera-hack           - Caltrans (427)           - HLS Conversion
- Bing/DuckDuckGo       - TfL (890)                
- Windy.com             - Netlas                   
                        - Live Env (2.6k)          
                        - Mass Port Scan (24)      
                        - User Provided (24)       
                        - Canon VB (187)           

                                                  BRUTE FORCE
                                                  - 50+ default creds/brand
                                                  - 6+ CVE exploits
                                                  - Hybrid auth schemes
```

## Files

### Documentation
- `docs/SESSION_REPORT_2026-08-24.md` - **NEW** session summary
- `docs/VBVIEWER_PIPELINE.md` - Canon VB pipeline
- `docs/CURRENT_STATE.md` - Live status
- `docs/BF_GUIDE.md` - Brute-force methodology
- `docs/CVE_GUIDE.md` - CVE reference
- `docs/VB_CAMERA_REFERENCE.md` - Canon VB models + protocol
- `docs/MASTER_PIPELINE_LOG.md` - This file
- `docs/FINAL_REPORT_AUG22.md`, `docs/ROUND{2,3,5,7,8,9}_*.md` - Round writeups

### Scripts (working)
- `camera_testing/run_pipeline.py` - Main orchestrator (continues running)
- `camera_testing/argus_ingest_v3.py` - Argus ingest
- `camera_testing/opencctv_ingest.py` - OpenCCTV ingest
- `camera_testing/trafficvision_full_ingest_v3.py` - TV catalog
- `camera_testing/caltrans_ingest.py` - Caltrans
- `camera_testing/tfl_ingest.py` - TfL
- `camera_testing/netlas_ingest.py` - Netlas
- `camera_testing/mass_scan3.py` - Mass scan
- `camera_testing/full_reprobe.py` - Re-probe
- `camera_testing/vbviewer_mjpeg_proxy.py` - MJPEG proxy :8767
- `camera_testing/vbviewer_stream_discovery.py` - Update VB CSV with streams
- `camera_testing/serve_viewer.py` - Web viewer :8765

### Scripts (Canon VB-specific)
- `camera_testing/vbviewer_probe.py` - Canon VB probe library
- `camera_testing/vbviewer_ingest.py` - Seed ingest
- `camera_testing/vbviewer_ingest_live.py` - Live ingest
- `camera_testing/vbviewer_ingest_webviewcams.py` - WebViewCams ingest
- `camera_testing/vbviewer_subnet_scan.py` - /24 subnet
- `camera_testing/vbviewer_host_scan.py` - Hostname scan
- `camera_testing/vbviewer_kaifu_scan.py` - LG/JP subdomains
- `camera_testing/vbviewer_port_scan.py` - Multi-port
- `camera_testing/vbviewer_internetdb_scan.py` - Shodan InternetDB
- `camera_testing/rtsp_scan.py` - RTSP port probe
- `camera_testing/rtsp_bf.py` - RTSP BF (Basic + Digest)
- `camera_testing/merge_vbviewer_to_master.py` - Merge to master
- `camera_testing/update_master_mjpeg.py` - Update with MJPEG URLs

### Brute Force
- `bruteforce/vbviewer_bruteforce.py` - Original Canon VB BF
- `bruteforce/vbviewer_bf_cve.py` - BF + 6 CVE exploits
- `bruteforce/apply_bf_results.py` - Apply cache to CSV
- `bruteforce/ultimate_bruteforce.py` - 1k creds × 25 brands
- `bruteforce/axis_bruter.py`, `axis_rockyou.py` - AXIS BF
- `bruteforce/smart_bruteforce.py` - Smart BF with brand detection
- `bruteforce/vendor_cves.py` - Vendor CVE database

### Core Libraries
- `camera_testing/csv_writer.py` - Atomic append w/ Windows lock
- `camera_testing/probe_lib.py` (v3) - 200+ probe patterns
- `camera_testing/cam_sniffer.py` - Vendor fingerprint
- `camera_testing/tier5_extractor.py` - HTML iframe/embed extractor
- `camera_testing/harvest_lib.py` - Cam harvesting utilities
- `camera_testing/descriptions.py` - Cam description generator
- `camera_testing/vbviewer_probe.py` - Canon VB probe
- `camera_testing/extract_location.py` - HTML location scraper
- `camera_testing/extract_exif.py` - JPEG EXIF GPS extractor
- `camera_testing/ip_freshen.py` - IP-API batch freshener
- `camera_testing/nvr_scan.py` - NVR/DVR scanner
- `camera_testing/bf_cameras.py` - HTTP Basic + RTSP brute forcer
- `camera_testing/brand_enrichment.py` - Vendor CVE annotation
- `camera_testing/full_reprobe.py` - Mass re-probe (?70k)
- `camera_testing/camera_hack_dump.py`/`probe.py`/`runner.py` - Cam-Hack
- `camera_testing/live_env_ingest.py` (v1, v2) - Windy + willytop8
- `camera_testing/insecam_2019_ingest.py` - 17k insecam URLs
- `camera_testing/fast_probe.py` - 120-thread URL probe
- `camera_testing/mass_port_scan.py` - 200+ /16 prefixes × 25 ports
- `camera_testing/windy_scraper.py` - Windy.com
- `camera_testing/ingest_user_urls.py`/`add_user_urls_minimal.py` - User URLs
- `camera_testing/orio_ingest.py` - Orio + Bergamo
- `camera_testing/dedup_csv.py` - URL dedup every 5 min
- `camera_testing/health_probe.py`/`health_probe_big.py` - Health checks

## Statistics

### CSV State (2026-08-24)
| Metric | Value |
|--------|-------|
| Total rows | 194,238 |
| Live | 194,143 (99.95%) |
| Auth-required | 83 (0.04%) |
| Brand coverage | 96.7% |
| Avg row size | ~640 bytes |
| File size | ~125 MB |

### Canon VB State
| Metric | Value |
|--------|-------|
| Total | 232 cams |
| Live w/ MJPEG | 130 (10+ fps via proxy) |
| Auth-required | 91 (Canon VB auth holds) |
| Anonymous wvhttp | 102 |
| Real creds unlocked | 2 (user:user) |
| Models | 24 unique |
| RTSP endpoints | 17 (likely Panasonic BB-HCM) |
| Countries | 9 |

## Continuous Operation

All ingestors run via `pythonw.exe` on Windows Task Scheduler. Logs at `camera_testing/<script>_*.log`. The pipeline runs 24/7 and adds ~50-100 cams/day from incremental discovery.

## Critical Constraints (DO NOT VIOLATE)

1. **CSV append-only with lock file** - never overwrite existing rows
2. **LF line endings** - not CRLF
3. **35-column schema** - preserve header order
4. **Atomic writes** - tmp file + os.replace
5. **URL dedup** - skip duplicate URLs across sources
6. **Lock file O_EXCL** - cross-process safe
7. **Stale lock detection** - 60s timeout before override
8. **MJPEG proxy port 8767** - main viewing interface
9. **Web viewer port 8765** - main search interface
10. **FFmpeg at** `C:\Users\eli6-admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\`
