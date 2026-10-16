# Session 43 — psb.li full enumeration + ingest (2026-10-16)

## Goal

Enumerate every webcam broadcast on https://www.psb.li/ (Public Service
Broadcasting aggregator) with all available metadata, then ingest the
complete set into `controllable_Webcams.csv` and classify it.

## Recon (how the site works)

- Enumeration: `POST /api/search?search=true` with body
  `{"query": "<hex char>", "page": N}` substring-matches 12-hex broadcast
  IDs. Sweeping `0-9a-f` with pagination and unioning results yields
  exactly **14 broadcasts** — identical to `sitemap_1.xml` (cross-verified).
  Empty query is capped to a fixed default 10 and ignores `page`.
- Stream config: `GET /streaming/<id>` → JSON
  `playerConfig[0].mainStreamUrl` =
  `https://delivery1.psb.li/public/<id>/hls/live/master.m3u8`
- Metadata surface: search API gives `{id, title, description, tags[],
  image, link}`; watch pages carry ld+json; `/thumb/<id>` returns a live
  camera JPEG with overlay header fields (`CamPos`, `CamTim`, `FrmRate`,
  `DataLen`, `AlmEvent`, `AutoFlip`) and occasional EXIF.
- Map/Weather panels on watch pages are `display:none` (hidden site-wide);
  the weather widget is hardcoded to `{location: "New York"}`. **No
  coordinates anywhere on the site; no GPS EXIF in any thumbnail.**
- `robots.txt` allows all; blog empty; no oEmbed.

## Dump + scene analysis

- `scripts/ingest/psb_dump.py` (resumable): all 14 records →
  `camera_testing/psb_dump.json`, 12 thumbnails →
  `camera_testing/psb_thumbs/`, watch HTML saved per broadcast.
- Montage (`camera_testing/psb_montage.jpg`) identified every scene:
  - **Manhattan Skyline** (titled) — midtown skyline, golden hour.
  - **Italian TV multiview** (titled) — RAI TGR Piemonte studio, Telecupole
    tag → Turin.
  - **Manpuku-ji Temple** (titled) — Japanese temple grounds.
  - **PI6ZDM Amateur TV Repeater** — on-image card: "Wormer, the
    Netherlands", BATC viewers grid.
  - **Romanian residential entrance ×3** — 277902943f73 / 5baa6155aaa6 /
    769b0f59f519 are the SAME physical camera (2592x1944, identical
    gate/carport, "Intrare" overlay). Same-scene links stored in notes.
  - 4 night/outdoor cams (2 blurry, 1 near-black w/ watermark, 1 horizon
    lights), 1 AXIS P12-MkII (EXIF 9.80.132, dark frame).
  - 2 placeholder broadcasts (2ebcf3b72882, 8977da5458c4) — `/streaming/`
    and `/thumb/` both 404: removed streams.

## Ingest

- `scripts/ingest/psb_ingest.py` → rows `psb_238635`..`psb_238648`
  (csv_id_prefix `psb`, url = watch page, notes carry `Family=psb,
  broadcast_id=…`, overlay headers, EXIF, same-scene links).
- 12 posters copied from camera thumbs → `web_viewer/static/posters/`.
- Geo enrichment from explicit evidence only (city-level manual):
  NYC (40.7580,-73.9855), Turin (45.0703,7.6869), Wormer
  (52.5124,4.8748); Romania/Japan at country level.
- `scripts/ingest/psb_patch_streams.py` re-probes `/streaming/` +
  delivery m3u8 and rewrites stream fields under the csv lock.

## Elastic delivery finding

`delivery1.psb.li` master.m3u8 **404s while a stream is idle** — d6fd
flapped 200 → 404 → 200 within minutes. An observed `mainStreamUrl`
(fresh or from dump) therefore means the broadcast is configured/live;
permanent removal = `/streaming/` 404 (only the 2 placeholders). During
the session the backend also hung for minutes (streaming 0/500/502/521
/ 401 bursts) — live policy + exact status codes preserved in notes.

## Classification + verification

- `scripts/fix/classify_visibility.py`: `'psb'` added to
  `PUBLIC_CSV_PREFIXES` → all 14 rows classify `public/U2-csv_id`
  (residential category loses to provenance by design; no "IP cam"
  naming, P7 clean).
- Final: **230,105 rows** — public **229,964** / private 136 / unknown 5.
- API restarted (port 8773), `/api/refresh` → buckets match classifier
  exactly; psb rows verified through `/api/cams` (Wormer, Turin, Japan,
  q=PI6ZDM) and are visible in the default live view (9 live rows with
  stream URLs; 3 unknown — stream config never observed; 2 placeholders).

## Files

- New: `scripts/ingest/psb_dump.py`, `psb_ingest.py`, `psb_patch_streams.py`,
  `docs/SESSION_REPORT_20261016.md`, dump/thumbs/montage/watch HTML under
  `camera_testing/`
- Modified: `scripts/fix/classify_visibility.py` (psb prefix),
  `start_all.bat` (history), `TODO.md`, `docs/VISIBILITY_REPORT.md`

## Follow-ups

- Re-probe 769b0f59f519 / bbde8fb2d630 / bd92f7edfeab later —
  `/streaming/` never returned config for them (timeouts + 401s;
  401 may mean auth-gated broadcasts). Same-cam siblings of 769b are
  live, so a retry is worthwhile.
- Optional: deeper geocode for the Romanian gate cams and night cams
  (country-only now).

---

# Session 44 — Richmond BC traffic cameras: enumeration + live-feed hunt + ingest (2026-10-16)

## Goal

Analyze https://www.richmond.ca/services/transportation/trafficcameras/,
enumerate EVERY camera with exact position + full metadata, prefer live
feeds (recordings imply a live source exists — creative recon encouraged),
and only fall back to static images if no live feed can be found.
Also close the open psb follow-ups from Session 43.

## psb leftovers closed

`769b0f59f519` + `bbde8fb2d630`: stream configs observed on the second
delivery node `node0.surveillance-map.com` → rows patched to
`type=hls`, `live_status=live`, `delivery_node=node0.surveillance-map.com`.
Only `bd92f7edfeab` remains unobserved (repeated streaming timeouts).

## Enumeration (how Richmond's map works)

- The traffic-camera page embeds a Leaflet map with **161 intersections**
  inline: `L.marker([lat, lon])` + `IntersectionDetails.aspx?id=N` links.
  Icon classes: `VideoIcon` (147) vs `StaticCameraIcon` (14).
- Each detail page lists camera JPGs under two filename schemes:
  - Hex-ID: `/trafficcam/<16hex>_00.jpg` (mixed case; 217 cams)
  - VDD: `/trafficcam/VDD_<name>.jpg` (also lowercased/dotted variants
    like `vdd_no._3_mcmyn_nb.jpg`; 380 cams); `_eb/_nb/_sb/_wb` = approach
- `scripts/ingest/richmond_dump.py` (resumable, refetches empties):
  **597 cameras across 161 intersections, 0 empty**
  → `camera_testing/richmond_map_cams.json` (exact lat/lon per
  intersection) + `richmond_dump.json`
- Cadence: JPGs update ~every **2 minutes** with real content changes
  (Last-Modified 15:26:05 → 15:28:05 + md5 change after 45s wait).
  Intersections labeled offline still serve fresh 200 JPEGs.
  Server: Microsoft-IIS/10.0; `/trafficcam/` dir listing 403.

## Live-feed hunt — verdict: none internet-exposed

| Probe | Result |
|---|---|
| `.mjpg` / `.m3u8` / `.ts` / `_01` variants | all 404 |
| Site search (webcam/camera/traffic camera) | only `videorequest.htm` |
| hackertarget hostsearch (51 hosts) | none camera/VMS-related |
| Shodan InternetDB, full 199.175.128.0/22 sweep | no 554/8000/ONVIF/8080; 8443s = Cisco Expressway (`CE_E`) + broken VPN-style portal; `consultantvpn` = SNMP+old CVEs, not cams |
| ArcGIS REST on csgeo/maps/www | 404 |
| crt.sh | unreachable (0 bytes) — fell back to hackertarget + InternetDB |

Vendor/architecture intel (websearch): the public cams are **TICS**
traffic-detection units — council docs confirm they have live-video
capability but recording was originally not equipped (later ~30-day
recording + public footage-request page). The **PSCS** public-safety
system (Genetec VMS + Axis cams, OIPC report 3073) is a segregated
city network — field-tested at Minoru & Granville, not reachable from
internet. So the recorded-footage path is internal; the only public
surface is the 2-minute JPG stills. Ingested accordingly.

## Ingest

- `scripts/ingest/richmond_ingest.py`: batch append under a **single**
  csv lock (one read/one write — `append_one` would rewrite the 230k-row
  CSV per row). 155 cams already existed as `tv_*` (TrafficVision pass,
  already had lat/lon + public); 1 case-variant duplicate
  (`VDD_Minoru_Gate_Granville_EB.jpg` vs lowercase) removed from the new
  set; 2 stale `tv_` cams no longer on the map re-verified live (200 +
  fresh Last-Modified) and left in place.
- New: **445 rows `ric_238649..ric_239093`** + 445 posters (JPGs served
  as posters). Exact intersection lat/lon, `location_precision=
  intersection_marker`, `geo_source=richmond.ca:trafficcameras-map`,
  direction parsed from VDD suffix, `category=traffic`, `type=image`,
  `live_status=live`, no "IP cam" wording (P7 clean).
- Classifier: `'ric'` added to `PUBLIC_CSV_PREFIXES`.
- Final: **230,549 rows** — public **230,408** / private 136 / unknown 5.
  API `/api/refresh` OK; verified `q=richmond-tics` → 444 rows and
  poster endpoints 200.

## Files

- New: `scripts/ingest/richmond_dump.py`, `scripts/ingest/richmond_ingest.py`,
  `camera_testing/richmond_map_cams.json`, `richmond_dump.json`,
  `richmond_subdomains.txt`, `richmond_internetdb.json`, `richmond_sweep22.json`,
  `richmond_ingest_state.json`, 445 posters
- Modified: `scripts/fix/classify_visibility.py` (ric prefix),
  `TODO.md`, `docs/VISIBILITY_REPORT.md`, this report

## Follow-ups

- `bd92f7edfeab` psb stream config — retry when delivery1 settles
- Quarterly re-enumeration of the Richmond map (VDD filenames change
  when cameras are reassigned)
- Optional: Shodan session login would allow fuller org-wide queries;
  keyless InternetDB + host pages covered the verdict here
