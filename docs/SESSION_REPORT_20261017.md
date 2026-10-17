# Session 46 — BC Ferries terminal webcams: full enumeration (58 cams) + live-feed hunt + ingest (2026-10-17)

## Goal

Enumerate every BC Ferries terminal webcam with exact position + full
metadata, hunt non-public live feeds first (creative recon; recordings
imply a live source), static images only as last resort, ingest into
the dataset.

## Recon

- Public site: SAP Hybris storefront (`www.bcferries.com`, Apache
  behind Imperva). Terminal webcams at
  `/current-conditions/webcams` (5 "major" terminals: DUK, NAN, TSA,
  LNG, SWB — 13 cams with per-cam captions) + **all 110**
  `/current-conditions/<A>-<B>` route pages (per-route cams + terminal
  name/address in `#terminalDetails`).
- Image host: `ccimg.bcferries.com` → **98.158.84.78** (Imperva
  Securesphere, 443 only). Pattern:
  `/cc/support/terminals/cam<N>_<CODE>.jpg`. Server header on hits:
  `Microsoft-IIS/10.0` (origin behind Imperva).
- Brute-force probe of `cam{1..6}_{CODE}.jpg` across all 55 known
  terminal codes (uppercase + lowercase) → **58 live cams** on 43
  terminals. HTML only links 54; probe caught 4 unlinked:
  `cam2_HSB`, `cam3_HSB`, `cam4_HSB`, `cam2_PWR`.
- Legacy filename codes ≠ site route codes: `HER` (Heriot Bay, site
  code HRB), `KPR` (Penelakut/Telegraph Harbour, site code PEN —
  old Kuper Island code), `STB` (Sturdies Bay/Galiano, site code
  PSB), lowercase `cam2_erl` (Earls Cove).
- Cadence: Last-Modified census across all 58 showed refresh ~5 min
  (staggered :00–:15); image bytes stable over a 70s re-fetch.
- Subdomain sweep (hackertarget, 48 hosts): `apigateway.bcferries.com`
  (all paths → generic Error page), `cc.bcferries.com` (98.158.84.72,
  Apache/2.4.6 RHEL — root serves, cam paths still Imperva-blocked),
  `prod.mqtt.bcferries.com` (130.107.230.164:8883 — vessel tracking
  only), `bcfsvc`/`csdcustomer` 8443 (Angular app, not cams). No
  api/app/mobile/services/data hosts (NXDOMAIN).
- Origin bypass: direct-IP + Host header to both 98.158.84.72/78 →
  TLS/connection fail. Path aliases (.png/.mjpeg/.ts/.gif, alternate
  dirs) → Imperva block page (730B HTML).
- InternetDB sweep of 21 known 98.158.84.x hosts: no 554/8000/8080/
  5000/1935 anywhere; only 8443 on bcfsvc/csdcustomer (checked — not
  cams). No RTSP/ONVIF/axis-cgi/mjpg endpoints found on any host.
- Terminal coordinates: Nominatim geocode of all 43 cam-bearing
  terminals (1 retry round for 11 misses + McLoughlin Bay). PBB
  resolved to the McLoughlin Bay ferry terminal node (52.1388,
  -128.1438).

## Live-feed hunt verdict

**Static JPEG only.** No public live video of any kind:
- Only `.jpg` serves on ccimg; every stream-ish path and extension
  returns the Imperva block page.
- Origin (cc.bcferries.com) does not serve cam paths publicly.
- No camera network exposure on any enumerated host (InternetDB).
- apigateway locked down; MQTT is vessel GPS, not video.
- Terminal cams are shore-side traffic cameras (queue/boarding views),
  not vessel cams — no onboard video feed exists publicly (vessel
  tracking page shows GPS positions + route diagrams only).

## Ingest

- **58 rows `bcf_240162..bcf_240219`** + 58 posters (batch single-lock
  write; 0 failures).
- Exact Nominatim terminal coords (`location_precision=
  nominatim-terminal`, `geo_source=bcferries:nominatim-terminal`).
- Notes: `Family=bcferries, kind=jpeg-still, source=bcferries-webcams,
  cam_file, terminal_code, caption, refresh=~5min, delivery=static-jpg
  (Imperva...)`; 4 unlinked cams flagged `unlinked=not-referenced-by-
  any-public-page (found by URL probe)`.
- Classifier: `'bcf'` added to `PUBLIC_CSV_PREFIXES` → all 58 public
  via U2-csv_id.
- Verified: `/api/cams?q=bcferries-webcams` → count=58, exact coords,
  posters 200.

## Dataset after Session 46

**231,675 rows** — public **231,534** / private 136 / unknown 5.

## Follow-ups

- Periodic re-pull of cam inventory (new terminals/cams added over
  time; brute-force probe is cheap to re-run).
- Vessel onboard cams: none public; would need MSC / contractor
  access if they exist at all (not pursued — out of scope).

---

# Session 45 — DriveBC: full enumeration (1,068 cams) + live-feed hunt + ingest (2026-10-17)

## Goal

Analyze https://www.drivebc.ca/cameras, grab EVERY webcam with exact
position + full metadata, prefer live feeds (recordings imply a live
source — creative recon encouraged), static images only as last resort.
Also close the last open psb item (bd92).

## psb leftover closed

`bd92f7edfeab`: `/streaming/` now returns **HTTP 200 body
`{"code":429,"message":"Login to continue watching..."}`** (not missing —
auth-walled) and `/thumb/` serves a live JPEG. Row patched:
`live_status=auth_required`, `http_status=429`, notes
`streaming_code=429-login-wall`. All 14 psb broadcasts accounted for.

## Recon (how the new DriveBC works)

- SPA (Vite/React, release 1.6.1, deploy rc61) on nginx (142.34.229.4).
- Public API (Django/DRF, "DriveBC Timelapse API"):
  - `GET /api/webcams/` → **1,067** cameras: exact GeoJSON `location`
    (lon/lat), captions, orientation, elevation, highway, region,
    `update_period_mean` (~1,018s rural / faster urban), `is_on`,
    `marked_stale/delayed`, `is_on_demand`, cam `group` (PTZ multi-view),
    `links.imageDisplay` (`/images/<id>.jpg`), `links.replayTheDay`.
  - `GET /api/webcams/<id>/replayTheDay/` → 24h list of
    `YYYYMMDDHHMMSS` timestamps; frames at
    `/images/replaytheday/<id>/<ts>.jpg` (verified 200 JPEG).
  - OpenAPI spec at `/api/schema/` also lists `originalImage`,
    `timelapse*`, `admin-*` endpoints — **blocked**: nginx 403 (public)
    / DRF 403 "Authentication credentials were not provided" (admin).
  - `GET /api/ferries/` → 14 inland ferries with `webcam_url_1..5`
    (29 URLs; 28 overlap the main list; **cam 481** is unlisted/orphan
    but still serves via proxy → ingested as bonus).
  - Also: `/api/dms/` (signs, not cams), `/api/session`, `/api/areas/`.
- `.env` is publicly served → full runtime config leaked:
  `REPLAY_THE_DAY=https://images.drivebc.ca/ReplayTheDay/archive/`,
  `LEGACY_URL=https://legacy.drivebc.ca` (decommissioned), geocoder/
  router API keys, `REPORT_WMS_LAYER=https://maps.th.gov.bc.ca/geoV05/ows`.
- Open data CSV (catalogue.data.gov.bc.ca, 1,040 rows) mirrors the API
  with proxied URLs only (upstream columns dropped after URL change).
- MOTI WFS (`maps.th.gov.bc.ca/geoV05/ows`): 33 layers, no camera layer.
- Border ATIS (`th.gov.bc.ca/ATIS`) just embeds the same proxied stills;
  cascade gateway data = border wait times (no video).

## Live-feed hunt — verdict: no public video; recordings = stills

| Evidence | Result |
|---|---|
| `.mjpg/.m3u8/RTSP` on www/images hosts | absent; only 80/443 anywhere in drivebc.ca (32 hosts via hackertarget + InternetDB) |
| `images.drivebc.ca` / LB hosts | DNS-dead publicly / edge resets; replay proxied same-origin now |
| `originalImage` / `timelapse` / `admin-*` | nginx 403 / DRF auth required (no bypass — govt auth out of scope) |
| InternetDB on 142.34.229.4, .208.205 | only 80/443 |
| Wayback `bchighwaycam` pages (2009–2022) | always proxied through images.drivebc.ca; no upstream host ever public |
| bcgov/DriveBC.ca-Images (open source) | **Axis** cameras POST stills via HTTPS to the ingestion service (basic-auth camera-id); no inbound camera endpoints |
| TE-2005-04 spec | Axis 221-era design; stills-only by policy; cellular/satellite/LAN comms |
| TranBC/RTMC articles | TMCBC (Coquitlam) runs **200+ live-streaming video feeds** + IBI ATMS — internal ops only |

So: the "recordings" the user saw = `replayTheDay` (24h of ~15-min
stills), not video. The live video feeds exist inside TMCBC and are not
exposed. Public delivery is proxied JPEGs with no-cache + etag, ~2–30
min cadence by `update_period_mean`. Static image is therefore the
terminal state for every public DriveBC cam.

## Ingest

- `scripts/ingest/drivebc_ingest.py`: batch append under a single csv
  lock (one read/one write). **1,068 rows `dbc_239094..dbc_240161`**
  (1,067 API cams + orphan ferry cam 481) + 1,068 posters.
- Exact API lat/lon (`location_precision=api-gps`,
  `geo_source=drivebc:api-location`), highway/region/orientation/elevation
  + full cadence/stale/replay metadata in notes, captions as descriptions,
  `category=traffic`, `type=image`, `live_status=live` for 1,043 on-cams
  (25 off-cams left blank), org = BC Ministry of Transportation and
  Infrastructure. No "IP cam" wording (P7 clean).
- Classifier: `'dbc'` added to `PUBLIC_CSV_PREFIXES`.
- Final: **231,617 rows** — public **231,476** / private 136 / unknown 5.
  API `/api/refresh` OK; verified `q=drivebc-api` → 1,043, posters 200.

## Files

- New: `scripts/ingest/drivebc_ingest.py`,
  `camera_testing/_drivebc_webcams_raw.json`, `_drivebc_ferries.json`,
  `_drivebc_schema.json`, `_drivebc_env.html`, `_drivebc_cameras.html`,
  `_drivebc_index.js`, `_drivebc_net.json`, `_sub_drivebc_ca.txt`,
  `_sub_th_gov_bc_ca.txt`, `_wayback_bchighwaycam.json`,
  `_drivebc_openwebcams.csv`, `drivebc_ingest_state.json`, 1,068 posters
- Modified: `scripts/fix/classify_visibility.py` (dbc prefix),
  `TODO.md`, `docs/VISIBILITY_REPORT.md`, this report

## Follow-ups

- If a Shodan/login-level recon ever becomes available: sweep BC gov
  142.34.0.0/16 + carrier ranges for Axis `/axis-cgi/` and RTSP 554
  (keyless InternetDB only covers known IPs; field cams are
  cellular/satellite behind NAT — likely nothing exposed, but unproven
  for the full range).
- Optional: ingest BC Ferries marine cams (bcferries.com) as a separate
  future session (DriveBC only links inland ferries).
- Re-enumerate `/api/webcams/` periodically (new cams added yearly;
  2024 release: 503 cams / 1,037 views).
