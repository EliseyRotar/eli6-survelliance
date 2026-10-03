# Camera Discovery Pipeline — Run Log

## What
Heavy-duty multi-source cam discovery + probing pipeline. Finds public/private IP cameras via many sources, probes them for live streams, geo-locates them, appends to `controllable_Webcams.csv`. Runs continuously.

## Started
2026-08-22 02:10:38 UTC (initial prototype)

## Files
- `camera_testing/run_pipeline.py` — main orchestrator, runs forever
- `camera_testing/probe_lib.py` — probe patterns (H.264 → MJPEG → JPEG)
- `camera_testing/harvest_lib.py` — DDG, insecam, opentopia, brand-dork queries
- `camera_testing/csv_writer.py` — atomic row appender with Windows lock retries
- `camera_testing/pipeline_log.txt` — ongoing activity log

## Source Mix
1. **insecam.org** country pages: 50+ country pages scraped in seq (1.5 s/req). High yield — `insecam-viewer` URLs are mostly live.
2. **DuckDuckGo HTML** dorks (3 sets):
   - DDG_RES (30): Hipcam, HiSilicon residential cams — `"/web/tmpfs/snap.jpg"`, `"/web/tmpfs/mjpeg"`, etc.
   - DDG_BRANDS (45): ALL webcam brands with public IP cam signature — Foscam, Reolink, Amcrest, Hikvision, AXIS, etc.
   - DDG_HACK (10): `inurl:"axis-cgi"` various.
3. **Bing HTML** (planned) — 23 dorks; kept as fallback.

## Probe Strategy
`probe_one()` probes each host with **top 14 patterns by weight** (3 s timeout each). Patterns are ordered by *yield* not pure H.264 preference:

```
1. /cgi-bin/faststream.jpg?stream=full&fps=16  (most common public stream)
2. /control/faststream.jpg
3. /faststream.jpg
4. /cgi-bin/viewer/video.jpg  (insecam-style — Bosch/Canon/Panasonic public streams)
5. /viewer/video.jpg
6. /cgi-bin/video.jpg
7. /cam_1.cgi, /cam_1.mjpg  (WebcamXP 5)
8. /-wvhttp-01-/video.cgi (ACTi wvhttp)
9. /axis-cgi/mjpg/video.cgi (AXIS MJPEG)
10. /mjpg/video.mjpg  (generic)
11. /web/tmpfs/mjpeg  (Hipcam Hi3510)
12. /ISAPI/Streaming/channels/101/httppreview  (Hikvision H.264)
13. /axis-cgi/media.cgi?container=matroska&videocodec=h264  (AXIS H.264)
14. /cgi-bin/mjpeg  (generic MJPEG)
```

A successful probe is recorded as a `best_w` score. We accept any stream kind:
- `mjpeg-multipart` (multipart/x-mixed-replace) — w=50
- `matroska` (video/x-matroska) — w=70
- `mp4` (video/mp4) — w=60
- `jpeg-large` (image/jpeg + cl≥5000) — w=12

Family tags inferred from path: `axis`, `hikvision`, `hipcam`, `webcamxp`, `mobotix`, `canon`, `mjpeg-faststream`, `mjpeg-wvhttp`, `insecam-viewer`, etc.

## CSV Schema (33 cols)
The appender appends one row per discovered live cam.

| col | field | sample |
|-----|-------|--------|
| 0 | idx | auto-increment from current max |
| 1 | project_name | city-prefixed family type |
| 2 | url | root URL e.g. http://host:port |
| 3 | live_stream_url | direct stream (H.264 > MJPEG > JPEG) |
| 4 | type | video-h264 / video-h264-matroska / video-mjpeg / image |
| ... | ... | ... |
| 19 | country | from ip-api |
| 20 | region | from ip-api |
| 21-29 | city, zip, lat, lon, isp, org, asn | from ip-api |
| 31 | notes | brief |
| 32 | csv_id | disc_NNNN |

## Quality rules
- **No duplicates**: any host with same `(host, port)` is ignored on second probe.
- **Timeout**: 3.0 s per path; total per-host budget ≤ 14 paths × 3 s = 42 s max (typical: 8-15 s).
- **Geo rate**: ip-api.com allows 45 req/min from same IP → 1.4 s sleep between appends.
- **CSV lock retries**: `csv_writer.append_one` retries 5× with backoff for Windows `PermissionError`.

## Observed Yield
- Round 1 insecam: **27 cands → 24 live (89%)** including mostly European/AU residential cams.
- 24 cams added to CSV in 90 s of probe+geo.

## Subsequent rounds
- `ddg_res`/`ddg_brands`/`ddg_hack` queries are slow (1 s sleep × 30+45+10 = 90+ s/round) and currently return low yield due to DDG anti-bot. We rely on insecam + Bing for steady supply.

## Next rounds plan
- Add: WebcamXP-list scraper (peers -> /cam_1.cgi with port fuzz)
- Add: Shodan InternetDB as free tier (https://internetdb.shodan.io/{ip}) → ASN-aware discovery
- Add: host range fuzz on EU residential ASNs (RIPE, T-Com, Orange, Vodafone, etc.)

## After this run completes, you'll see ~hundreds of cams added to CSV, each with a direct browser/ffplay-able stream URL.
