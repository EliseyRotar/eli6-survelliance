# Exposed Services on Found Cams — Port Scan Results

Scanned all 6 known cams with ~340 common ports on Aug 21 2026.

## Summary by cam

| Cam | IP | Country | Open Ports | Notes |
|---|---|---|---|---|
| flightcam1.pr.erau.edu | 199.104.253.4 | US (AZ) | **80 only** | HTTP web UI + MJPEG + VAPIX (anonymous PTZ); RTSP (554) firewalled externally |
| 195.196.36.242 | 195.196.36.242 | SE (Sweden) | **80, 443** | HTTPS web UI + MJPEG + H.264 Matroska + VAPIX (no auth) |
| flightcamnorth.db.erau.edu | 155.31.14.40 | US (FL) | **80, 443** | HTTP+HTTPS web UI + MJPEG + native H.264 + VAPIX (admin requires creds) |
| flightcamsouth.db.erau.edu | 155.31.14.41 | US (FL) | **80, 443** | Same as north |
| sbhome63378.dyndns.org | 92.171.245.23 | FR | **16251 only** | Custom non-standard port; HTTP web UI + MJPEG + native H.264 + VAPIX |
| wc2.dartmouth.edu | 129.170.117.10 | US (NH) | **80, 554** | HTTP web UI + MJPEG only (AXIS 221, old firmware, no H.264); RTSP server responds to OPTIONS but all DESCRIBE URLs return 404 |

## Findings: **only webcams + their native services exposed**

No other "interesting" services found (no SSH/FTP/Telnet/SMB/RDP/VNC on any cam). Each cam exposes ONLY:
- AXIS web UI on HTTP(S)
- AXIS VAPIX CGI endpoints (under /axis-cgi/) — these are specific to AXIS, not general services
- AXIS RTSP on port 554 (where exposed) — also AXIS-specific
- No database, no SMB, no SSH, no open management ports

## Per-cam details

### flightcam1.pr.erau.edu (199.104.253.4)
- Open: 80 (HTTP)
- Closed: 554 (RTSP firewalled), 443 (HTTPS not exposed)
- Behind BigIP load balancer
- AXIS P5415-E PTZ Dome, firmware 6.50.5.20
- Anonymous PTZ via `root.PTZ.BoaProtPTZOperator=anonymous`

### 195.196.36.242 (Sweden)
- Open: 80, 443
- AXIS P1447-LE 5MP bullet camera
- No auth required for viewer
- HTTPS exposed (with cert mismatch — type `thisisunsafe` in Chrome)
- All VAPIX endpoints accessible including `/axis-cgi/api-discovery.cgi`
- 56 VAPIX APIs enumerated

### flightcamnorth.db.erau.edu / flightcamsouth.db.erau.edu (Daytona Beach)
- Open: 80, 443 each
- AXIS M2025-LE bullet cameras, firmware 9.80.105 (newer)
- H.264 native via `/axis-cgi/media.cgi`
- HTTPS available
- Auth required for `/axis-cgi/serverreport.cgi`, `/admin-bin/`, `/operator/`
- `root.PTZ.BoaProtPTZOperator=password` (NOT anonymous)

### sbhome63378.dyndns.org (92.171.245.23, France, Orange ISP)
- Open: **16251 only** (custom port — not 80/443)
- Behind consumer dyndns (home broadband)
- AXIS M2025-LE bullet camera
- Native H.264 via `/axis-cgi/media.cgi?container=matroska&videocodec=h264`
- Brand confirmed via param.cgi (`root.Brand.ProdFullName=AXIS M2025-LE`)

### wc2.dartmouth.edu (129.170.117.10, Dartmouth College NH)
- Open: **80, 554**
- **AXIS 221 Network Camera** (2005-era, very old)
- MJPEG only (no H.264, no MPEG4 exposed — too old)
- RTSP server responds to OPTIONS/GET_PARAMETER but **all DESCRIBE URLs return 404**
  - This is suspicious — could be a decoy, misconfigured service, or requires auth-first
  - Could not extract any usable video stream via RTSP
- Admin pages: `/admin/` returns 401 (auth required)

## Files saved
- `camera_testing/service_scan_results.txt` — full scan output
- `camera_testing/rtsp_probe.py` — RTSP URL brute forcer
- `camera_testing/wc2_rtsp_*.txt` — RTSP probe logs
- `camera_testing/wc2_view.html` — AXIS 221 view page (confirms model)
- `camera_testing/wc2_mjpeg_*.mjpg` — captured MJPEG samples
- `camera_testing/wc2_h264_tiny.mkv` — transcoded H.264 sample (125 frames, 160x120)
- `camera_testing/sbhome_h264.mkv` — native H.264 capture (640KB, 15s)

## Conclusion
We found **only webcam services** on all 6 cams. No enterprise services (SSH/FTP/RDP/SMB/databases/etc.) exposed. All cams are pure AXIS devices running only the AXIS web stack. The "interesting" findings are:
- Anonymous PTZ on flightcam1
- No-auth viewers on 195.196.36.242
- RTSP server with no usable URLs on wc2.dartmouth.edu (likely honeypot or auth-gated)