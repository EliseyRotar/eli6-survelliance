# -*- coding: utf-8 -*-
"""Prepend Session 47 sections to SESSION_REPORT_20261017.md and TODO.md."""

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"

REPORT_SECTION = """# Session 47 — Spain/Andorra: eTraffic gap-close + 5-source enumeration + 2,086-row rectification (2026-10-17)

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
"""

TODO_SECTION = """## ✅ Session 47 (2026-10-17) — Spain/Andorra: eTraffic gap-close + 5-source enum + 2,086-row rectification

### Done
- Live-feed hunt verdict (eTraffic): **stills-only** — image host
  serves only `{id}.jpg` (all video variants 404), `/api/*` + infocar
  legacy paths are Akamai SPA fallbacks, origin blocked (port 8020 =
  web-filter interstitial), dgt.es viewer taken down 09-oct-2026,
  community tools stills-only. Only real live video found: YouTube
  embeds on camarasdgt.es webcam pages
- eTraffic API decoded (XOR 0x66): 1,960 cams; + pre-env `993` +
  10 alive legacy-only + 3 CDX-only (`18`,`103`,`1040`) = **1,974
  DGT inventory**; CSV had 1,933 → 41 missing
- DATEX2 v3.7 (3.7 MB, 1,960 devices) = province/road/lastUpdate
  enrichment; getPMVs 2,517 signs / getFilteredData 987 incidents
  = not cams
- New sources enumerated: Euskadi GV 131, Vitoria 40, Catalunya SCT
  WFS 164, Andorra Mobilitat API 68, Cantur 6, camarasdgt YT webcams
  (IP firewalled → Wayback: 2 alive embeds, 1 already in CSV)
- Id-space dedupe vs CSV (http/https + subdomain tolerant): ando/vit
  fully present, eusk 122/131, gencat 98/159 (+29 dead legacy
  Andorra-border URLs already covered by `tv_` rows) → **58 new rows**
- Ingested `idx 240220..240277` (dgt 41 / eusk 9 / cnt 6 / cat 1 /
  web 1) + 48 posters; all `visibility=public` after prefix add
  (`dgt,eusk,cnt,web,cat` in PUBLIC_CSV_PREFIXES)
- Census: all 1,933 existing DGT rows live-checked → 1,912 live,
  **21 dead (404)** marked `image-404@2026-10-17`
- **Rectified 2,086 disc_ rows**: argus-v2 mirror had DGT cams in
  Belgium ("Grimbergen, Spain" lat 50.95), Euskadi cams in Alaska,
  Catalonia cams in Germany, all `category=public` → official
  names/coords/region/road/category from eTraffic API + DATEX2 +
  opendata.euskadi.eus + gencat WFS + mobilitat.ad
- 8 Nominatim geocodes (6 Cantur + Benidorm beach; Altea pre-had)
- 231,733 rows; public **231,592** / private 136 / unknown 5;
  API refreshed + verified (q=Cantur → 7)

### Next
- Retry camarasdgt.es once firewall ban lifts: `_es_arch4.py` resume
  (255 Wayback listing pages) + full 324-page `/webcam/` subtree →
  more YouTube live embeds
- Retry `trafikoa.eus` from another network (9 eusk rows lack
  live_status/posters)
- Catalog gaps: Madrid + Barcelona city cams, Donostia/Bilbao
  (403 WAF), Sant Boi ArcGIS, 32 gencat ids retired from current WFS
- Periodic DGT re-census (21 cams died since last ingest)

"""


def prepend(path, text):
    with open(path, encoding="utf-8") as f:
        old = f.read()
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text + old)
    print("prepended:", path, "+", len(text), "chars")


prepend(ROOT + r"\docs\SESSION_REPORT_20261017.md", REPORT_SECTION)
# TODO: insert after the title line
todo_path = ROOT + r"\TODO.md"
with open(todo_path, encoding="utf-8") as f:
    lines = f.readlines()
title = lines[0]
rest = "".join(lines[1:])
with open(todo_path, "w", encoding="utf-8", newline="") as f:
    f.write(title + "\n\n" + TODO_SECTION + rest)
print("inserted TODO section")
