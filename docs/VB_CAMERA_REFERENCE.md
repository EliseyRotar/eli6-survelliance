# Canon VB Camera Reference

Complete technical reference for Canon VB / WebView Livescope (WV-HTTP) cameras.

## What is Canon VB?

Canon VB is Canon's line of professional network cameras that use the **WebView Livescope (WV-HTTP)** protocol for streaming and administration. Despite the user-facing name "VBViewer" (also used for Panasonic BB-series), these are **Canon cameras**, not Panasonic.

VBViewer is **NOT** related to Panasonic BB-HCM cameras (which use similar UI but different firmware).

## Models Identified (24 unique)

### VB-C Series (Compact PTZ)
- **VB-C10R** (PTZ, network camera, 1 cam found)
- **VB-C50** (Fixed box, 3 cams found)
- **VB-C60** (Compact PTZ, **77 cams found** - most common!)
- **VB-C500D** (Compact mini-dome, 3 cams found)

### VB-M Series (Professional Box/PTZ)
- **VB-M40** (Box camera, **35 cams found**)
- **VB-M42** (Box camera, **27 cams found**)
- **VB-M600D** (Dome, 4 cams found)
- **VB-M600VE** (Vandal-resistant dome, 1 cam)
- **VB-M620D** (Dome, 1 cam)
- **VB-M641VE** (IR dome, 2 cams)
- **VB-M700F** (Box, 2 cams)
- **VB-M740E** (Box, 4 cams)
- **VB-M741LE** (IR, 2 cams)

### VB-S Series (Ultra-compact)
- **VB-S30D** (Compact dome, 1 cam)
- **VB-S805D** (Compact mini-dome, 1 cam)
- **VB-S900F** (Box, 6 cams found)
- **VB-S905F** (Compact box, 1 cam)

### VB-R Series (Speed Dome / PTZ)
- **VB-R10VE** (Vandal-resistant speed dome, 5 cams)
- **VB-R11VE** (IR speed dome, 1 cam)

### VB-H Series (Compact)
- **VB-H41** (Box, 8 cams)
- **VB-H43** (Box, 8 cams)
- **VB-H610VE** (IR dome, 1 cam)
- **VB-H630VE** (IR dome, 2 cams)

## Identification Signatures

### HTTP Server Header
```
Server: VB              <- Old firmware (4.0)
Server: VB/1.0          <- VB-M40/M42
Server: VB/2.0          <- VB-S30D
Server: VB/3.0          <- VB-C60
Server: VB/5.0          <- VB-R10VE
```

### Title
```html
<title>Network Camera</title>     <- All VB cams
```

### WV-HTTP Endpoints
```
/-wvhttp-01-/open.cgi           <- Session establishment
/-wvhttp-01-/close.cgi          <- Session close
/-wvhttp-01-/image.cgi          <- JPEG snapshot
/-wvhttp-01-/getoneshot         <- Single JPEG frame
/-wvhttp-01-/video              <- MJPEG multipart stream
/-wvhttp-01-/GetSystemInfo      <- System info
/-wvhttp-01-/GetCamInfo         <- Camera info
/-wvhttp-01-/CamCtrl            <- PTZ control
/-wvhttp-01-/GetDate            <- Date/time
/-wvhttp-01-/GetMenu            <- Menu
```

### Web Viewer
```
/viewer/live/index.html        <- Main HTML viewer (28811 bytes)
/viewer/live/wv.js              <- WV-HTTP JS library
/viewer/admin/index.html       <- Admin panel (auth required)
/admintools/index.html         <- Admin tools (auth required)
```

## Streaming Protocol (WV-HTTP)

### Session Establishment
```http
GET /-wvhttp-01-/open.cgi?seq=<random>&priority=0&v=h264:<size> HTTP/1.1
Host: <camera_ip>

Response:
s:=<session_id>
s.origin:=<internal_lan_ip>:<port>
s.duration==0
s.priority:=0
v:=h264:1280x720:0:30000
v.h264.cbr==2048
```

**Important**: Build URL manually - `requests` library URL-encodes the `:` in `v=h264:1280x720` to `%3A`, which Canon rejects with "Invalid Parameter Value".

### JPEG Snapshot (Anonymous)
```http
GET /-wvhttp-01-/image.cgi?v=jpg:1280x720 HTTP/1.1
Host: <camera_ip>

Response: image/jpeg, 32KB-250KB depending on resolution
```

### MJPEG Stream (Requires Session)
```http
GET /-wvhttp-01-/video?<session_id>&seq=1 HTTP/1.1
Host: <camera_ip>

Response: multipart/x-mixed-replace; boundary=boundary
Content-Type: multipart/x-mixed-replace

--boundary
Content-Type: image/jpeg
Content-Length: 4458

<JPEG bytes>
--boundary
Content-Type: image/jpeg
Content-Length: 4456

<JPEG bytes>
...
```

### Resolution Options
- `v=jpg:320x180` - 320x180 (default)
- `v=jpg:320x240` - 320x240 (may default to 320x180)
- `v=jpg:640x480` - 640x480
- `v=jpg:1280x720` - 1280x720 (most cams)
- `v=jpg:1280x960` - 1280x960 (some cams)
- `v=jpg:1920x1080` - 1920x1080 (high-end only)

### Compression (H.264 only)
- `v.h264.cbr==2048` - 2Mbps constant bit rate
- Can request lower bitrate with `v.h264.cbr==512` for slow connections

## MJPEG Frame Rates

Tested frame rates via the MJPEG proxy:

| Camera | Frame Rate |
|--------|------------|
| 68.66.157.38 (USA workshop) | 0.3 fps |
| 61.122.58.10 (Japan) | 1.9 fps |
| 125.206.33.49 (Japan) | 0.0 fps (dead) |
| webcam.bakio.eus (Spain) | **10.0 fps** |
| cam06.kaifu-intra.jp (Japan) | 1.0 fps |
| 202.174.60.121 (Mt Fuji) | **9.2 fps** |

**Note**: Frame rate is limited by the camera's hardware, not the stream itself. Older cams like VB-M40 max at ~2fps, newer VB-S/R cams can do 10+ fps.

## Internal IP Exposure

Many Canon VB cams expose their **internal LAN IP** via the `s.origin:` field in `open.cgi`:

```
s.origin:=192.168.1.10:80
```

This means the camera is sitting on a private network behind NAT, and the external IP we see is different.

**Example**: Cam `202.174.60.121` (Mt Fuji) has `s.origin:=192.168.1.10:80` - it's at `192.168.1.10` internally.

## Authentication

### Endpoints with Auth

- `/admin/index.html` - Admin panel
- `/admin/login.html` - Admin login
- `/admin/cgi-bin/aw_cam` - Admin CGI
- `/admintools/index.html` - Admin tools
- `/cgi-bin/aw_cam` - CGI control
- `/-wvhttp-01-/open.cgi` - Session creation (on some models)

### Endpoints WITHOUT Auth (Anonymous Access)

- `/-wvhttp-01-/getoneshot` - JPEG snapshot (most cams)
- `/-wvhttp-01-/image.cgi` - JPEG snapshot (most cams)
- `/-wvhttp-01-/video` - MJPEG stream (most cams)
- `/-wvhttp-01-/GetSystemInfo` - System info (most cams)

### Authentication Realm
```
WWW-Authenticate: Basic realm="User"
WWW-Authenticate: Digest realm="Administrator"
```

## RTSP Support

Canon VB cams **DO NOT** support RTSP. The WV-HTTP protocol is proprietary.

Some cameras may expose RTSP on port 554 via firmware hacks, but standard Canon VB cams don't.

## Common Ports

| Port | Service | Auth |
|------|---------|------|
| 80 | HTTP admin + WV-HTTP | Mixed |
| 443 | HTTPS (rare) | Mixed |
| 8080 | Alt HTTP (rare) | Mixed |
| 5000 | Secondary HTTP (rare) | Mixed |

Canon VB cams typically run on port 80 only.

## Discovery Techniques

### 1. Server Header
```bash
curl -s -I http://IP/ | grep -i server
Server: VB/2.0
```

### 2. Title Check
```bash
curl -s http://IP/ | grep -i title
<title>Network Camera</title>
```

### 3. Anonymous JPEG Test
```bash
curl -sI http://IP/-wvhttp-01-/image.cgi?v=jpg:1280x720 | head -1
HTTP/1.0 200 OK
```

### 4. System Info
```bash
curl -s http://IP/-wvhttp-01-/GetSystemInfo
version=VB-M42 Ver. 1.0.0
number_of_active_clients=3
start_time=Thu, 09 Jul 2026 12:50:01 +0900
```

### 5. Internal IP Discovery
```bash
curl -s "http://IP/-wvhttp-01-/open.cgi?seq=1&v=h264:1280x720"
s.origin:=192.168.1.10:80
```

## Geographic Distribution (from Pipeline)

| Country | Cams |
|---------|------|
| Japan | 148 |
| USA | 32 |
| Spain | 6 |
| Canada | 3 |
| Germany | 1 |
| Finland | 1 |
| Australia | 1 |
| Italy | 1 |

Most Canon VB cams are deployed in **Japan** (148 of 187 total) on local government networks for traffic/weather/landmark monitoring.

## Browser Support

Canon VB Viewer uses **ActiveX/Java applet** in legacy viewers - **does NOT work in modern browsers**.

To view Canon VB cams in modern browsers:
1. Use the **MJPEG proxy** to convert WV-HTTP streams to standard multipart
2. Use `<img src="...">` tags which natively support multipart MJPEG
3. Or use VLC media player with the direct WV-HTTP URL

## Production Use

Canon VB cams were popular in Japan for:
- City/town traffic monitoring (板柳町, 名寄市, 大江町, etc.)
- Ski resort cameras (Mt Fuji, 高天ヶ原)
- Tourist attractions (Mt Fuji, Lake Ashi)
- Construction site monitoring
- Weather observation

The cameras are largely **out of production** (released 2008-2018), but many remain deployed in Japan and other countries.

## Related Products (Not Canon VB)

The user originally mistook Canon VB cams for "VBViewer" / Panasonic. These are **different** products:

| Product | Vendor | Protocol |
|---------|--------|----------|
| Canon VB | Canon | WV-HTTP (proprietary) |
| Panasonic BB-HCM | Panasonic | Custom CGI |
| Panasonic BL-C | Panasonic | Custom CGI |
| i-PRO WV | i-PRO (Panasonic) | WV-HTTP (Canon-compatible) |

i-PRO cameras use a Canon-compatible WV-HTTP protocol and can be accessed via the same `/-wvhttp-01-/` endpoints.
