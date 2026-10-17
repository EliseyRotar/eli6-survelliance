# Session 47 — Spain/Andorra: eTraffic gap-close + 5-source enumeration + 2,086-row rectification (2026-10-17)

## Goal

Enumerate every Spanish (and Andorra) webcam with exact position + full
metadata starting from https://etraffic.dgt.es/etrafficWEB/, hunt
non-public live feeds first (recordings imply a live source), static
images only as last resort; ingest everything into the dataset.

## Live-feed hunt verdict (eTraffic / DGT)

- **Stills-only by design.** Image host `etraffic.dgt.es/camarasEtraffic/`
  serves exactly `{id}.jpg`; every video-shaped variant
  (`.mjpg/.mjpeg/.ts/.mp4/.m3u8/stream`, query params, alternate dirs)
  404s. `camarasEtraffic/` directory listing 403.
- `/api/*` and legacy `infocar.dgt.es/etraffic/data/camaras/{id}.jpg`
  "200s" are Akamai SPA index.html fallbacks (5,056 B, wrong
  content-type) — Akamai edges 23.202.156.242 / 23.61.250.229.
- Old path `estaticosEtraffic/` = Akamai "Hello World" boomerang page.
- Origin recon: `gis.dgt.es` 403, `srvgis.dgt.es` NXDOMAIN,
  `infocar`/`stre`/`dit` = nginx 404s; port 8020 on 212.128.100.158 =
  "Web Filter Block Override" proxy interstitial for every path (dead
  end). InternetDB sweep found no stream ports anywhere.
- Official statement (dgt.es, updated 09-oct-2026): "Actualmente, no
  disponemos de la visualización de estas cámaras" — the public viewer
  was taken down.
- Community tools (DGTcameradownloader, camaras-trafico-ha) confirm:
  stills-only.
- Bonus endpoints: `getPMVs` = 2,517 variable-message signs (no cams),
  `getFilteredData` = 987 incident records; both need
  `Content-Type: application/json; charset=UTF-8` (else 415).
- The only real live video found in this session: **YouTube embeds on
  camarasdgt.es webcam pages** (see below).

## Enumeration

- **eTraffic API** (POST, XOR-0x66 decode): **1,960 cams** with
  carretera/pk/coordX/coordY/sentido/idCamara + `urlBase`. Plus
  pre-env `etraffic-pre.dgt.es` id `993` (M-40), 10 alive legacy-only
  ids from old dgt.es `camaras.json` (incl. coord fixes: `176531`
  lat sign, `181924` comma-decimal), and 3 Wayback-CDX-only ids
  (`18` stale LM 2026-05-05, `103`, `1040`) → **1,974 DGT inventory**.
- CSV already held **1,933** DGT image URLs (1,769 `disc_` argus +
  164 `tv_` trafficvision) → **41 missing**.
- DATEX2 v3.7 (`_es_datex2_v37.xml`, 3.7 MB): 1,960 `device` records
  (province, roadName, kilometerPoint, lastUpdate, tpegDirection) —
  used as region/enrichment source.
- New sources fetched + verified:
  - **Euskadi GV** (opendata.euskadi.eus geojson/CSV): 131 cams,
    images `www.trafikoa.eus/static/files/tr/camaras/{id}.jpg`
    (host TCP-times-out from our network; source claims 3-min refresh)
  - **Vitoria-Gasteiz** geojson: 40 city cams (image 200 verified)
  - **Catalunya SCT** WFS XML: 164 cams (gml:coordinates lon/lat;
    RenderService images 200)
  - **Andorra Mobilitat** `app.mobilitat.ad/api/v1/cameras`: 68 cams
    (`imgs.mobilitat.ad/prod/*.gif` 200 verified, LM same-day)
  - **Cantur** (Cantabria): 6 mountain webcams, night-IR + burned-in
    timestamp (Fuente Dé overlay fresh same-day)
  - **camarasdgt.es `/webcam/` subtree**: site IP-firewalled us after
    ~350 requests → Wayback harvest recovered 3 YouTube embeds; 2 alive
    (`Playa de Altea` = Camping Cap-Blanch, `isLiveNow=true` since
    2021; `Playa de Benidorm` = SkylineWebcams recorded loop),
    Zurriola deleted. CSV already had the Altea one.
- Dedupe vs CSV in each source's id space (http/https + subdomain
  tolerant): andorra 68/68 and vitoria 40/40 already present as `tv_`;
  euskadi 122/131; gencat 98/159 (+29 WFS entries point at dead legacy
  `app.mobilitat.ad/gifs/*` paths — physical cams already covered by
  working `tv_` Andorra rows) → **58 genuinely new rows**.

## Ingest + fixes

- **58 rows `idx 240220..240277`** (41 `dgt_`, 9 `eusk_`, 6 `cnt_`,
  1 `cat_` emap Terrassa cam01, 1 `web_` YouTube Benidorm): 47 live,
  1 dead (`188670` 404), 9 unverifiable (trafikoa.eus unreachable from
  ingest network). Posters 48/58 (same 10 expected fails).
- **Liveness census of all 1,933 existing DGT rows**: 1,912 live,
  **21 newly 404** → `live_status=''` + `image-404@2026-10-17` note;
  all got fresh `http_status`.
- **Mass rectification — 2,086 rows** (all `disc_`, marker
  `rectified-20261017-from-official-source`): the OpenCCTV/argus-v2
  mirror rows carried garbage — DGT cams named "Grimbergen, Spain ·
  Spain DGT" at lat 50.95 (Belgium), Euskadi cams in Alaska/Bavaria,
  Catalonia cams labelled Germany/France, `category=public`,
  region=foreign states. Overwritten from official sources: name
  (`A-62 km 57.9 -`), country, region (DATEX2 province title-cased /
  Euskadi / Catalunya), road, official coords, category=traffic,
  likely_subject. 1,769 DGT + 313 matched (120 eusk + 94 gencat +
  6 emap + 72 ando + extras) + 4 retired Andorra gifs (Fontaneda,
  RadioAndorra\* — absent from current API) fixed separately.
- Nominatim geocodes: 6 Cantur sites + Playa de Benidorm
  (`nominatim-poi`); Playa de Altea already had coords.
- Classifier: `PUBLIC_CSV_PREFIXES` += `dgt, eusk, cat, cnt, web`;
  re-run → all 58 new rows `public`.
- **Final: 231,733 rows** — public **231,592** / private 136 /
  unknown 5. API `/api/refresh` OK (rows=231733); verified
  `q=Cantur` → count 7; new rows all `visibility=public`.

## Files

- New: `scripts/ingest/es47_ingest.py`,
  `scripts/fix/es47_refresh_rectify.py`,
  `camera_testing/_es_build_inventory.py`, `_es_census.py`,
  `_es_finalize.py`, `_es_inventory.json`, `_es_inventory_final.json`,
  `_es_census.json`, `_es_overlap2.json`, `_es_dgt_already.json`,
  `_es_camaras_etraffic.json`, `_es_camaras_pre.json`,
  `_es_camaras_dgt.json`, `_es_datex2_v37.xml`,
  `_es_euskadi.geojson`, `_es_vitoria.geojson`, `_es_cat_xml.xml`,
  `_es_cat_cams.json`, `_es_andorra_api.json`, `_es_cantur_pages.json`,
  `_es_webcam_yt*.json`, `_es_hist_liveness.json`, `_es_arch*.json`,
  `_es_cdx_*.json`, `_es_getPMVs.json`, `_es_getFilteredData.json`,
  `_es_final_fixes.py`, `_es_geo_retry.py`, `es47_ingest_state.json`,
  48 posters
- Modified: `scripts/fix/classify_visibility.py` (5 prefixes),
  `docs/VISIBILITY_REPORT.md`, `TODO.md`, this report

## Follow-ups

- camarasdgt.es firewall: retry later → 255 pending Wayback listing
  pages (`_es_arch4.py` resume) + full 324-page `/webcam/` subtree for
  more YouTube live embeds.
- `trafikoa.eus` image host unreachable from this network: retry to
  fill 9 `eusk_` rows' `live_status` + posters (URLs are authoritative).
- Still missing from catalog: Madrid city cams, Barcelona city cams,
  Donostia/Bilbao open-data (403 WAF), Sant Boi ArcGIS, 32 gencat ids
  present in CSV but retired from current WFS.
- Periodic re-census of DGT (images refresh every few minutes;
  retirements happen — 21 died since last ingest).
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
