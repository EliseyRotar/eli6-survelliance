# AXIS M2025-LE Flightcams at Embry-Riddle Daytona Beach

**Status:** LIVE (both cams)
**Domains:** flightcamnorth.db.erau.edu, flightcamsouth.db.erau.edu
**IPs:** 155.31.14.40, 155.31.14.41
**Model:** AXIS M2025-LE Network Camera (bullet-style, fixed)
**Location:** Embry-Riddle Aeronautical University, Daytona Beach FL campus
**View:** Daytona Beach International Airport (KDAB) — north cam + south cam

## Discovery
Found by brute-force DNS scan of `*.db.erau.edu` patterns (`cam.db`, `cam1.db`, `cam2.db`, `flightcamnorth.db`, `flightcamsouth.db`). The `flightcam*` hostnames resolved via reverse-DNS to IPs 155.31.14.40/41. The other 3 (`cam.db.erau.edu`, `cam1.db`, `cam2.db`) resolve to 155.31.10.217/218/219 but are firewalled (DNS-only, no open ports).

A broader /24 scan of `155.31.{10-15,20-100}.0/24` (4318 IPs) found ONLY these two new cams. They are the only public-facing AXIS cams at Daytona Beach.

## Streams

| Stream | URL | Notes |
|---|---|---|
| MJPEG | http://flightcamnorth.db.erau.edu/axis-cgi/mjpg/video.cgi | Default, no auth |
| MJPEG-1280 | http://flightcamnorth.db.erau.edu/axis-cgi/mjpg/video.cgi?resolution=1280x720 | HD |
| **H.264** | http://flightcamnorth.db.erau.edu/axis-cgi/media.cgi?container=matroska&videocodec=h264&resolution=1280x720 | **Native H.264 — works!** |
| JPG snapshot | http://flightcamnorth.db.erau.edu/axis-cgi/jpg/image.cgi?resolution=1280x720 | Single JPEG, no auth |
| HTTPS | https://flightcamnorth.db.erau.edu/ | HTTPS supported! |

(Same URLs apply to flightcamsouth.db.erau.edu)

## Key tech specs (from VAPIX params)

- **Model:** AXIS M2025-LE (network camera, bullet form factor)
- **Firmware:** 9.80.105 (build 1, Apr 03 2025) — much newer than Prescott's 6.50.5.20
- **Hardware:** Axis Artpec-5 SoC, MIPS architecture, HardwareID 727
- **Serial:** B8A44F263009
- **H.264 Profiles:** Baseline, Main, **High** (all supported!)
- **Max resolution:** 1920x1080 (16:9) + 22 other sizes
- **HTTPS:** YES (with valid cert chain)
- **H.264 installation enabled:** yes
- **HTTPS + ONVIF + RTSP + WebSocket + Privacy mask (max 32) + SD card recording + Local storage (disk encryption) + Motion (10 windows) + GuardTour (100 max) + Temperature control + Heater + LightControl**
- **No PrivacyMask enabled by default** (but hardware supports up to 32)

## Auth model

- **PTZ operator = `password`** (NOT anonymous like Prescott's flightcam1) — needs valid creds to move
- These are **fixed bullet cameras** anyway (no mechanical PTZ, just digital PTZ)
- `/axis-cgi/serverreport.cgi` and `/admin-bin/` → HTTP 401 (auth required for admin)

## Useful endpoints (all HTTP 200 anonymous)

- `/axis-cgi/mjpg/video.cgi` (MJPEG)
- `/axis-cgi/media.cgi?container=matroska&videocodec=h264&...` (H.264)
- `/axis-cgi/jpg/image.cgi?resolution=WxH` (snapshot)
- `/axis-cgi/param.cgi?action=list&group=root.<X>` (param dump)
- `/axis-cgi/param.cgi?action=list` (full 812-line dump)
- `/axis-cgi/serverreport.cgi` (returns 401)
- `/axis-cgi/api-discovery.cgi` returns **404** even on newer firmware 9.80 — AXIS only enabled it on certain newer OS versions

## Cam page (modern AXIS SPA)

```
GET /view/index.shtml
```
- Title: "AXIS"
- Bundle.js SPA (main.732dcaaa294fe0e96488.bundle.js)
- HTTPS-ready

## File artifacts saved

- `flightcamnorth_db_erau_edu_brand.txt` — model info
- `flightcamnorth_db_erau_edu_params.txt` — full VAPIX dump (812 lines)
- `flightcamnorth_db_erau_edu_ptz.txt`, `flightcamnorth_db_erau_edu_props.txt`
- `flightcamnorth_db_erau_edu_view.html` — view page
- `flightcamnorth_h264.mkv` (1.5MB, 15s, 1280x720 H.264 Main profile)
- `flightcamnorth_db_erau_edu_mjpeg.mkv` (488KB, 4s MJPEG)
- `flightcamnorth_db_erau_edu_snap_*.jpg` (174KB, 1280x720)
- Same files for flightcamsouth (`flightcamsouth_*.mkv`, `_snap_*.jpg`)

## Live .bat files created

- `camera_testing/flightcamnorth_h264_cam.bat` — direct H.264 ffplay
- `camera_testing/flightcamsouth_h264_cam.bat` — direct H.264 ffplay

## Reproduction

```bash
# Direct H.264 (no transcode needed, native!)
ffplay "http://flightcamnorth.db.erau.edu/axis-cgi/media.cgi?container=matroska&videocodec=h264&resolution=1280x720"

# Snapshot
curl -s "http://flightcamnorth.db.erau.edu/axis-cgi/jpg/image.cgi?resolution=1280x720" -o north.jpg

# Param dump
curl -s "http://flightcamnorth.db.erau.edu/axis-cgi/param.cgi?action=list&group=root.Brand"
```

## Ethical notes
- Cams are open to public MJPEG + H.264 streams (no auth for viewer)
- Admin endpoints require creds (PTZ operator=password)
- Located at KDAB airport — no privacy concerns, public airspace