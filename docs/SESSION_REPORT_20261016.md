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
