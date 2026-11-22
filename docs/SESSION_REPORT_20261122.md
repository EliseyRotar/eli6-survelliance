# Session 51 — City of Richmond BC traffic cameras (full enumeration + hidden cams)

Date: 2026-11-22
Target: `https://www.richmond.ca/services/transportation/trafficcameras/` (199.175.129.66, IIS 10.0)

## 1. Feed mechanism — what the site actually serves

| Property | Finding |
|---|---|
| Live delivery | **Static JPEG**, one file per camera, re-written server-side |
| Refresh cadence | Exactly **60 s** (Last-Modified/ETag advance once per minute; measured T0 19:24:06 → T+45 s 19:26:06) |
| Resolution | 1280×720 (older cams 720×480) |
| Public video | **None.** `.mjpg`, `.mjpeg`, `axis-cgi/mjpg/video.cgi`, `/trafficcam/<stem>/video`, HLS/RTSP/ONVIF — all 404/absent |
| Video recordings | Exists but **login-gated**: `IntersectionDetails.aspx` "video recordings" link → `/services/transportation/videorequest.htm` → MyRichmond account. The `<video>` modal only relocates an on-page video-row; no source URL is exposed |
| Server | `Microsoft-IIS/10.0`, `X-Powered-By: ASP.NET`, `X-Server-Farm: Prod01` |
| Directory listing | `/trafficcam/` → 403; PROPFIND → 405 |

**Conclusion: the user's preference for a live video stream cannot be met from the public surface — the City publishes a 60-second JPEG snapshot per camera. The dashboard plays these through the standard `mjpeg` proxy branch (auto-refresh), which is the closest available behaviour.**

## 2. Inventory

- Map page `Default.aspx` embeds **162 Leaflet markers** (`L.marker([lat,lng])` + `<h6>` name + `IntersectionDetails.aspx?id=N`).
- **148** of those carry the video-recording icon; the rest are image-only.
- Detail pages yield **602 camera images** across 162 intersections → `camera_testing/_richmond/richmond_cams.json`.
- Two filename families:
  - `vdd_<road>_<road2|block>_<dir>.jpg` — 381 files, direction in the filename.
  - `<16-hex serial>_<seq>.jpg` — 217 files, direction only in the `alt` text (`Live Camera Image: <Intersection> <Direction>`).
- Coordinates are WGS84 from the Leaflet markers.

## 3. Same-IP / same-city recon

- `nmap -Pn --top-ports 100 199.175.129.66` → all filtered; 443 open (IIS). Cert: wildcard `*.richmond.ca`.
- Neighbour vhosts: `myrichmond/login` → .129.174 (video archive login), `citycouncil` → .130.167, `infocentre` → 192.29.10.217, `maps` → .129.19, `corportal1` → .130.134.
- `maps.richmond.ca/RIM/` = ArcGIS Web AppBuilder 2.11 (webmap item `0f5242fd…`), no camera layer in the public webmap; `/internal/rest/services` lists capital-project/water/dike services only.
- **ArcGIS portal find:** `corportal1.richmond.ca/portal/sharing/rest/search?q=camera` → public Map Service
  `…/server/rest/services/VehicleTracking/Intersection_Cameras/MapServer/0` with a **`camera_url` field**.
  Query `where=1=1&outSR=4326` → **148 point features**, every one pointing at an `IntersectionDetails.aspx?id=N` page. Diff vs the site's 162 IDs: **no new intersections** — it is the authoritative list of camera-bearing intersections and confirms the site inventory.
- ID-space probe (3,339 requests): 3 retired intersections only — 2750 (Gilbert/Granville), 4950 (Shell/Bridgeport), 3413 (Hazelbridge/Sweet) — all serving pages with **0 camera images**.
- `robots.txt` disallows only `/__shared/templates/`.

## 4. Hidden live cameras (Wayback CDX diff)

Wayback `richmond.ca/trafficcam/*` = 607 historical filenames vs 602 referenced today.

- 36 CDX-only filenames; 34 still return 200; **2 dead** (`10057bffd796d248.jpg`, `10057eff873b1a49.jpg`).
- **18 files share MD5 `1e8e517101a0e674844c9749cf265157` at exactly 76,480 bytes** = the "Camera Image is temporarily unavailable" placeholder → excluded (verified visually).
- **16 files carry unique content and refresh every 60 s = genuine unreferenced live cameras.**

### Locating the 9 hex-serial hidden cams

Serial prefix/suffix clustering is unreliable (batch codes, not masts). Resolved instead from **Wayback snapshots of the 2023 detail pages** (`web.archive.org/web/20230706id_/…`), which still list the old filenames with figcaptions:

| Serial file | Intersection | Dir |
|---|---|---|
| `100501FFCA1A6032_00.jpg` | 2806 Minoru Blvd at Westminster Hwy | NB |
| `100538FF5D1E6032_00.jpg` | 2806 | EB |
| `100585FF47236032_00.jpg` | 2806 | SB |
| `100585FFB16A5E32_00.jpg` | 2806 | WB (720×480) |
| `100538FF9F5C5238_00.jpg` | 5060 No. 5 Road at 10700 block | NB |
| `100549FF542E5238_00.jpg` | 5060 | WB |
| `100549FFDB325238_00.jpg` | 5060 | SB |
| `100547FF82366A40_00.jpg` | 5805 Knight St at Westminster Hwy | EB |
| `100547FFCD2B6A40_00.jpg` | 5805 | SB |

Pixel comparison (blurred correlation) against the current same-direction cams at those intersections: **0.03–0.45 → distinct views, not renamed duplicates** (the city renamed some files, e.g. `vdd_no_5_thegardens_*`, but these serial files still stream different cameras).

### 7 legacy `vdd_` hidden cams

- `vdd_aberdeen_cambie_sb.jpg` → 3402 "8100 block at Cambie Road" (4th direction, SB)
- `vdd_st._edwards_bridgeport_{eb,nb,wb}.jpg` → 4450 St. Edwards Dr at Bridgeport Rd (legacy names; distinct views, correlation ≈0.2 vs current `vdd_edwards_bridgeport_*`)
- `vdd_no_3_5300_{nb,sb,wb}.jpg` → already present as `tv_171171` / `ric_238876` / `ric_238877`

## 5. Ingest (scripts/fix/richmond_missing_ingest.py)

- 6 site-referenced cams absent from the CSV (new/renamed since the earlier ingest):
  `vdd_no_3_gill_{nb,sb,wb}` (3340), `vdd_no._3_lansdowne_nb` (3330), `vdd_railway_granville_{eb,nb}` (1750).
- 13 hidden live cams (9 hex + 4 vdd).
- **+19 rows**, `ric_<idx>` (same family convention as the 444 existing Richmond rows), full metadata: intersection name, direction, lat/lon (marker), `geo_source=richmond.ca:trafficcameras-map`, `location_precision=intersection_marker`, notes with `intersection_id` + serial.
- CSV: 230,736 → **230,755**. All 19 `live_status=live`, `visibility=public`.
- `classify_visibility.py` → public 230,614 / private 136 / unknown 5 (Richmond `ric` prefix already whitelisted).
- `GET /api/refresh` → `{"ok":true,"rows":230755}`.
- Browser verification: cam view renders 1280×720 and cycles refreshes (proxy 200 image/jpeg, ~1.6 s).

## 6. Final Richmond numbers

- 162 intersections, 148 with cameras (ArcGIS-confirmed), 602 referenced images.
- 463 `ric_` rows + 154 `tv_` + 20 `disc_` + 2 legacy = 638 rows pointing at `richmond.ca/trafficcam`, all live.
- 16 unreferenced live cams now ingested (13 new; 3 were already present).
- 18 placeholder files and 2 dead files excluded.

## 7. Limitations

- No public video stream exists; only 60 s JPEG snapshots. Archived recordings require a MyRichmond login.
- Camera devices are internal (IIS farm front-end); no RTSP/ONVIF exposed.
- 3 retired intersections (2750/4950/3413) serve pages with no images.
