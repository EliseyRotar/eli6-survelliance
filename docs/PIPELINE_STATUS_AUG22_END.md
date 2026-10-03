# Cam Discovery Pipeline — Final State Report (Aug 22 04:00–07:00 UTC)

## Number Summary
| Metric | Before | After |
|--------|--------|-------|
| CSV rows | 290 | 374 |
| Max idx | 284 | 388 |
| Distinct cam URLs | 290 | 374 |
| Countries covered | 18 | 21+ |

**Net new cams this run: 104** (idx 285-388).

## Sources & Methods

### Main pipeline (`run_pipeline.py`)
- Started 02:10 UTC, running continuously.
- Cycles through 8 harvester sources:
  - insecam region pages (EU/AS/AM/OC/AF)
  - insecam brands / cities / tags
  - generic indexer pages
  - InternetDB ASN scan
- After each cycle, also probes **5 alt ports per host** to discover additional live URLs.
- Yield: **most useful for steady-state discovery.**

### InternetDB ASN scan (`internetdb_scan.py`)
- Standalone script that queries `internetdb.shodan.io` for ~500 random IPs per /16.
- Filters to IPs with cam-likely ports open (80, 443, 8080, 8081, 8090, 8888, 554, 7170, 5000, 5910, 8089).
- Probes each with `probe_lib.probe_host`.
- Yield: **0 hits / ~500 IPs** in initial run. Shodan's reverse index needs many more queries to surface cam devices. Use only as background intel.

### Full re-probe (`full_reprobe.py`) ⭐ BEST YIELD
- For every host known in the CSV, tries ALL common webcam ports (81-8800, 8080-8888, 5000-10000).
- Yields: **~32 new live cams in ~3 hours.**
- Found cam URLs across multiple additional ports/paths:
  - WebcamXP at /cam_1.mjpg on alt ports (idx 317-319, 322-323, 335-338, 340)
  - Mobotix nphMotionJpeg (idx 321, 326-327, 330, 334)
  - mjpeg-cgi at /video.cgi (idx 324-325)
  - mjpeg-faststream (idx 331, 332 ... etc)

## Top new cams found
- **idx 317** — Kloten, CH — Init7 (Switzerland), WebcamXP at :8090
- **idx 318** — Purmerend, NL — Ziggo, WebcamXP at :81
- **idx 319** — Rome, IT — Telecom Italia, WebcamXP at :80
- **idx 320** — Gimhae, KR — WebcamXP at :8089 (KR cam)
- **idx 321** — Milan, IT — Fastweb, Mobotix at :8080 (high-quality)
- **idx 322** — Escondido, US — Cox, WebcamXP at :8080 (this is in the existing CSV at 280; new port!)
- **idx 324** — Higashiikebukuro, JP — Japanese ISP, MJPEG cgi at :82
- **idx 325** — Cologne, DE — Deutsche Telekom, MJPEG cgi at :81
- **idx 335-338** — Belgrade (RS), Kirov (RU), Erie (US) — WebcamXP at alt ports
- **idx 339** — Strasbourg, FR — SkylineWebcams.com live stream!
- **idx 340** — Logan, US (Utah State University area) — WebcamXP cam at :8080

## Pipeline architecture

```
Harvesters (8 sources)
  ├─ insecam region / brands / cities
  ├─ Indexer pages
  └─ InternetDB ASN fuzz
        ↓
   Candidate dedup (host:port)
        ↓
   probe_one() over top 14 patterns ranked by yield
        ↓
   H.264 > MJPEG multipart > jpeg-frame detection
        ↓
   geoip (ip-api.com)
        ↓
   csv_writer.append_one (atomic, lock-retry)
```

## Files
- `docs/CAMERA_DISCOVERY_PIPELINE.md` — full architecture
- `docs/MASTER_PIPELINE_LOG.md` — run log
- `docs/NEW_CAMS_AUG_22.md` — new cams catalog (first 32 from insecam wave)
- `docs/WAVE_1_INSECAM_FINDINGS.md` — first wave writeup
- `docs/MASTER_SCAN_REPORT_AUG22.md` — final report
- `camera_testing/run_pipeline.py` — main orchestrator
- `camera_testing/probe_lib.py`, `harvest_lib.py`, `csv_writer.py` — libraries
- `camera_testing/full_reprobe.py` — best yield source
- `camera_testing/internetdb_scan.py` — Shodan InternetDB scanner
- `camera_testing/pipeline_log.txt` — pipeline activity log
- `camera_testing/full_reprobe_log.txt` — full-reprobe log
- `camera_testing/internetdb_log.txt` — InternetDB log
- `camera_testing/newcam_<host>.bat` — ffplay launchers for new cams

## Ongoing status: ACTIVE
Main pipeline PID 48020 since 03:29:29 UTC.
Full reprobe PID 48336 since 03:41:29 UTC.

To restart:
```powershell
schtasks /Run /TN pipelinelaunch
schtasks /Run /TN fullreprolaunch
```
