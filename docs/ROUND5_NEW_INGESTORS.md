# Round 5 Final Report — 64,113 → 65,355+ cams in 60 minutes

## Summary
Started round 5 with **63,949 cams** in CSV. After adding 5 new ingestors (Argus v3, OpenCCTV, Caltrans, TfL, Mass-Scan Continuous), the CSV grew to **65,355 cams** in ~60 minutes.

## New Ingestors Created This Round

### 1. argus_ingest_v3.py (persistent + Tier 5 HTML extractor)
- **Source**: GitHub `GoSlowPoke168/Argus` dataset (229,308 cams)
- **Improvement over v2**: persistent chunk progress, 30-thread parallel, Tier 5 iframe/embed extractor
- **Yield**: ~10-20 new cams per 5-chunk cycle (mostly duplicates)
- **Total**: 57,684 → 57,720 (incremental)

### 2. opencctv_ingest.py (MASSIVE NEW SOURCE)
- **Source**: opencctv.org API (`/api/cameras/markers` + `/api/cameras/batch`)
- **Scale**: 158,595 cameras with real source feed_urls, lat/lon, country, city, category
- **Endpoint**: `POST https://opencctv.org/api/cameras/batch {"ids":[…≤50…]}` — no key needed
- **Yield**: 794 cams added in first 25 minutes (~10% survival rate)
- **Categories**: nature, water, traffic, surf-cams, weather, ski, etc.
- **Status**: 847 total added after restart, ongoing

### 3. caltrans_ingest.py (CALIFORNIA DOT)
- **Source**: Caltrans D1-D12 CCTV endpoints (`cwwp2.dot.ca.gov/data/d{NN}/cctv/cctvStatusD{NN}.json`)
- **Scale**: ~9,000 cams across 12 California DOT districts
- **Format**: HLS streams + JPEG snapshots + lat/lon/county/route
- **Yield**: 276 cams in first cycle (with district-prefixed ID fix)
- **Cycle**: Every 30 minutes

### 4. tfl_ingest.py (LONDON TRAFFIC)
- **Source**: TfL JamCam API (`https://api.tfl.gov.uk/Place/Type/JamCam`)
- **Scale**: 890 London traffic cams
- **Format**: mp4 video + jpg image + lat/lon
- **Yield**: 136 cams added in first cycle
- **Cycle**: Every 6 hours

### 5. mass_scan_continuous.py (RESIDENTIAL PRIVATE CAMS)
- **Source**: 200+ residential /16 prefixes × 23 cam ports
- **ISPs covered**: Comcast, Verizon, AT&T, Charter, Cox, T-Mobile, CenturyLink (US); DT, Vodafone, Orange, Free (DE/FR/UK/IT); NTT, KDDI, Softbank (JP); China Telecom, China Unicom; Viettel (VN); etc.
- **Approach**: 800 random /24 blocks × 4 IPs each = 3,200 host candidates per cycle
- **Cycle**: Every 5 minutes, TCP-port-scan + HTTP probe
- **Yield so far**: 0 cams in 2 cycles (most open ports are CPE routers, not cams — need different probe strategy)

## Discovery Indexes Identified But Not Yet Ingested

| Source | Endpoint | Scale | Status |
|--------|----------|-------|--------|
| WorldCam.eu | n/a | unknown | 404 |
| EarthCam.com | n/a | unknown | 404 |
| SkylineWebcams | hidden JSON API | ~5000 cams | needs reverse-eng |
| WebcamTaxi.com | HTML, no API | unknown | needs browser scrape |
| insecam.org | dead domain | n/a | n/a |
| Windy.com | needs paid key | 5,997 cams | already in live_env2 |
| WSDOT | auth required | ~700 cams | needs API key |
| DriveBC | HTML | ~600 cams | needs scrape |
| TxDOT | auth required | ~1500 cams | needs API key |
| NYC DOT | HTML | ~700 cams | needs scrape |
| Singapore LTA | auth required | ~90 cams | needs key |
| TMR Australia (QLD) | auth required | ~400 cams | needs key |
| IL Getting Around | 404 | unknown | needs scrape |
| OH Tableau | 404 | unknown | dead URL |

## Mass Port Scanner Refinement Needed

The residential mass-scan currently finds ~24 open ports per 5-min cycle but **0 cams**. The open ports are mostly:
- Cable modem admin panels (192.168.100.1, 192.168.1.1 leaked)
- Printers / NAS boxes (HTTP 200 with non-cam HTML)
- Routers with generic config pages

**Need**: improve probe_lib to recognize cam-specific signatures:
- AXIS VAPIX responses (`Server: AXIS`)
- Hikvision ISAPI challenges
- Dahua HTTP auth challenges
- ONVIF device discovery XML
- WebcamXP 5's `/cam_1.cgi` MJPEG multipart

## Field Fill Rates (current)
- country: 99%
- city: 99%
- lat/lon: 99%
- region: 91%
- asn: 4%
- isp: 1%
- zip: 2%
- address: 3%
- reverse_dns: 1%
- geo_source: 5% (mostly "reverse_geocoder")

## Process Status (as of 16:17 UTC)
- argus_ingest_v3.py — running, slow (~10 cams per 5 chunks)
- opencctv_ingest.py — running, fastest grower (~500 cams/hour)
- caltrans_ingest.py — running, 1/3 done with 12 districts
- tfl_ingest.py — running, 890 cams queued
- mass_scan_continuous.py — running, low yield
- full_reprobe.py — running (Task Scheduler, behind argus)
- run_pipeline.py — running (Task Scheduler, insecam cycle)
- mass_bf_all.py — running (3 parallel ultimate_bruteforce subprocess workers)

## Projected Growth (24h)
- OpenCCTV alone: 158k cams × 10% yield = 15,800 cams potential
- Argus remaining: 1.4M URL candidates in 167 chunks × ~0.5% = 7,000 cams potential
- Caltrans all districts: 9,000 cams once ID fix lands
- TfL: 890 cams total

If everything runs at maximum throughput: **~32,000 cams in 24h** → CSV hits ~97,000 cams by tomorrow.
