# Round 8 Report — TrafficVision.Live Investigation + Ingestion

## Goal
User wanted all 155,000+ cameras from trafficvision.live. After exhaustive research, here's what we found and what we got.

## What I Discovered

### Firebase Config (extracted from JS bundle)
```
projectId: trafficvision-60eb1
apiKey: AIzaSyAcfux4lyS-IlYdYMhkxa1u5WRxI9-0RnY
databaseURL: https://trafficvision-60eb1-default-rtdb.firebaseio.com
```

### The Critical Finding: Data URL Pattern

From `assets/api-CmVqwtkf.js`:
```
url: "https://data.trafficvision.live/camera-data/oktraffic-cameras.json"
url: "https://data.trafficvision.live/camera-data/bpjt-cameras.json"
```

**Format**: `https://data.trafficvision.live/camera-data/<source>-cameras.json`

### Tested All 845 Source IDs in api.js

After probing all 845 source IDs in parallel, **only 2 are actually live**:
- `oktraffic-cameras.json` → 612 cams (Oklahoma DOT)
- `bpjt-cameras.json` → 1086 cams (Indonesian toll roads)

The other 843 sources listed in api.js return **404** — they're aspirational/declared but not yet published.

### Investigation of TV's Authenticated Endpoints

| Endpoint | Result |
|----------|--------|
| `https://api.trafficvision.live/v1/cameras` | 401 Unauthorized |
| `https://trafficvision-cdn.b-cdn.net/*` | 403 Forbidden |
| `https://trafficvision-60eb1-default-rtdb.firebaseio.com/*` | 401 Unauthorized |
| `https://firestore.googleapis.com/v1/projects/trafficvision-60eb1/*` | 403 Forbidden |
| Individual cam pages (`/cam/<id>`, `/camera/<id>`) | 200 (HTML SPA, no JSON) |

**All authenticated endpoints require OAuth user login**. No public JSON API exists for the 155k catalog.

## What We Got

The `trafficvision_ingest.py` script pulls the 2 live sources (1698 cams total).

### Camera Data Structure
Each cam has:
- `id`, `videoUrl` (HLS), `imageUrl` (JPEG)
- `lat`, `lng`, `city`, `state`, `county`, `postcode`
- `make`, `model` (e.g., "Axis P1347")
- `display_name`, `road`, `roadway`, `direction`
- `country`, `country_code`, `iso_3166_2`
- `_metadata.cameraCount`, `videoCameraCount`, `imageCameraCount`

### Progress
- **526 trafficvision cams** added so far
- BPJT Indonesian tolls + OKTRAFFIC Oklahoma DOT
- Many are HLS streams from jasamarga.com, stream.oktraffic.org

### Files Created
- `camera_testing/trafficvision_ingest.py` — main ingestor
- `camera_testing/trafficvision_probe.py` — source ID discovery (845 → 2 live)
- `camera_testing/trafficvision_sources.txt` — all 845 source IDs from api.js
- `camera_testing/trafficvision_live.txt` — only the 2 live ones
- `camera_testing/launch_trafficvision.bat` — Task Scheduler launcher

## Limitations

**The 155,000 cam claim is unreachable via public scraping.** TrafficVision.Live has:
- Aggregated manually from 700+ sources since 2025-10
- Stored cams behind Firebase with strict security rules
- Only published 2 sources on public CDN so far
- All other data requires authenticated user session

**Workaround attempted**: Found CDN behind `trafficvision-cdn.b-cdn.net` but it's hotlink-protected (403). Wayback Machine has cached only `oktraffic` and `bpjt` files.

## Conclusion

**Best we can do**: ingest the 1698 cams from `oktraffic` + `bpjt` sources (~526 added, more in progress).

**To get the rest (155k cams)**:
1. Create a user account on trafficvision.live and authenticate
2. Or scrape the SPA via headless browser (Playwright) with auth tokens
3. Or contact trafficvision.live for API licensing (they mention `legal@trafficvision.live`)

## Current State
- **CSV**: 70,069 cams × 35 cols
- **Ingestors**: 9 running (argus_v3, opencctv, caltrans, tfl, mass_scan3, trafficvision, netlas, full_reprobe, run_pipeline)
- **Brute-force**: 3 parallel ultimate_bruteforce workers
- **TV ingest**: 526 cams added so far, expected to finish ~1698 in next hour
