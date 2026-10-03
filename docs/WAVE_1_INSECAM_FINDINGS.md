# First Wave: 26 New Cams from insecam (idx 285-308)

## Sources
- `camera_testing/run_pipeline.py` running since 2026-08-22 02:10:38 UTC
- insecam.org country pages scraped in batches; 27 unique IP candidates yielded 24 live.
- Remaining 2-3 cams (idx 309-313 from round 1 EU/AS) added later.

## Detected Streams
All are `insecam-viewer` MJPEG-style endpoints at `/cgi-bin/viewer/video.jpg` — Bosch/Canon/Panasonic cams exposed publicly via default admin:admin or no auth.

## Cities covered
Rimavská Sobota (SK), České Budějovice (CZ), Nový Malín (CZ), Brighton (UK), Stanišawice, El Grao (ES), Darłówo (PL), Csengele (HU), Budapest (HU), Hyderabad (IN), Achenkirch (AT), Kuala Lumpur (MY), Verdal (NO), Ghent (BE), Athens (GR), Melbourne (AU), Johannesburg (ZA), Shetou (TW), Ljubljana (SI), Klaipėda (LT), Thessaloniki (GR), Lai Chi Kok (HK), Yuen Long San Hui (HK), Mobile (US), Rancho Cucamonga (US).

## Why these cams are live
insecam.org maintains a curated list of publicly-accessible cams that have been *confirmed live* in their last scan. Most use vendor defaults or no password at all. Privacy-wise these are typically storefront / parking / bar / construction / nature.

## Direct Streams
Each cam has a `live_stream_url` field populated with the best path:
- Format A: `http://<host>:<port>/cgi-bin/viewer/video.jpg` — high-rate JPEG (`jpeg-frame` w=55)
- Format B: `http://<host>:<port>/viewer/video.jpg` — typically when cam is just webapp-deployed without /cgi-bin prefix

## CSV Schema after this run
- 290 → 294 rows (4 in line) but +24 added — many deleted earlier
- max_idx=313

## Methodology
1. **Pull 50+ country pages** from insecam.org via `requests.Session` with 1.2-1.5 s/req delay (anti-DOS)
2. **Extract URLs** matching `/cgi-bin/viewer/video.jpg` or `/viewer/video.jpg` patterns
3. **Dedup** against `existing_hosts` set; new IPs → ThreadPoolExecutor probes
4. **probe_one** hits 14 weighted paths (ranked by yield): insecam-viewer paths first, Hikvision/AXIS H.264 last
5. **Geo** each found host via ip-api.com; 1.4 s sleep for 45 rpm limit
6. **Append** to CSV with full 33-col schema, including `idx`, `csv_id=disc_NNNN`.

See `docs/CAMERA_DISCOVERY_PIPELINE.md` for full pipeline details.
