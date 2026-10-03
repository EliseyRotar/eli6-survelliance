# ARGUS CAM CLEANUP — STRATEGY REPORT

## 1. SCOPE & STATS

- **Total (argus) cams in CSV: 59,938** (out of 205,960 total rows = 29.1%)
- Generic name pattern: `<host-prefix> webcam (argus)` — e.g. `cameras webcam (argus)`, `atmsqf webcam (argus)`, `images-webcams webcam (argus)`
- **All share identical `description` text** (boilerplate): `"**cam view** IP camera (server signature recognised, family TBD) (single-frame JPEG; refresh-rate image viewer) - Hosted by **Argus Public Cams** (ISP / org). ..."`
- **`page_title` is always empty** for argus cams
- **`city`, `address`, `zip` are almost always empty**
- **`lat`/`lon` are OFTEN DEFAULT/WRONG** — only 369 of 59,938 have unique lat/lng; the rest collapse into ~10 default coordinates
- **`brand` is always `Argus Public Cams`**, `org` is the same
- **Top default lat/lng (suspect):** `43.793/142.280` (Japan Hokkaido), `22.248/114.150` (Hong Kong), `47.428/11.695` (Austria), `50.383/11.885` (Germany Thuringia), `36.57/-118.09` (US-West default), `40.5023/-0.1908` (Spain Avamet default)

## 2. THE GOLDEN KEY — `notes` COLUMN

The **`notes` field contains a unique `argus_id`** in the format:
```
Family=argus-public, kind=jpeg-frame, weight=8, source=argus-v2,
content-type=image/jpeg, server-banner-unknown;
argus_id=opencctv_<SOURCE>_<SPECIFIC_ID>
```

The **`SOURCE` segment is the most valuable classification field** — it tells you EXACTLY which upstream provider Argus scraped the cam from. Examples:
- `opencctv_windy_windy-1720011411` → Windy
- `opencctv_alertcalifornia_alertca-880` → ALERTCalifornia wildfire cams
- `opencctv_arcgis_cams_arcgis-IA-470416` → Iowa DOT via ArcGIS
- `opencctv_autostrade_autostrade-3443` → Italy Autostrade
- `opencctv_atv_atv-aomori` → Japan ATV weather
- `opencctv_state511_s511-NV-4875` → Nevada DOT 511
- `opencctv_avamet_avamet-c01m080e01` → Spain Avamet meteo network
- `opencctv_opendatahub_opendatahub-FERATEL_...` → South Tyrol Feratel (UUID per cam)

## 3. TOP UPSTREAM SOURCES (count of cams)

| Count | Source (from argus_id) | What it is | Real names available from |
|------:|------------------------|------------|---------------------------|
| 14,698 | `windy` / `windy-providers` (each is a unique windy-<id>) | Windy.com webcam catalog (webcams.windy.com) | Windy's own map API: `https://www.windy.com/-Webcams/webcams` or `https://api.windy.com/webcams/v2` |
| 9,086  | `cam_river` (cam.river.go.jp) | Japan MLIT river monitoring | https://cam.river.go.jp itself (location-coded URLs) |
| 4,443  | `windy` (via imgproxy.windy.com) | Windy imgproxy (same as above) | Windy API |
| 1,769  | `etraffic_dgt` (etraffic.dgt.es) | Spain DGT traffic cams | DGT official: https://infocar.dgt.es/etraffic/ |
| 1,475  | `webcams` (var. host: wzmedia, opensnow, houstontranstar, etc.) | State DOT traffic cams in US (CA, OR, MN, UT, NV, IA, IL, NY, FL…) | Each state's 511/transport site |
| 1,404  | `Skyline` (s52.nysdot.skyvdn.com) | NYSDOT | 511ny.org |
| 1,089  | `UT` (prod-ut.ibi511.com) | Utah DOT 511 | udot.utah.gov |
| 870    | `IA` (atmsqf.iowadot.gov) | Iowa DOT | iowadot.gov |
| 728    | `NV` (www.nvroads.com) | Nevada DOT | nvroads.com |
| 636    | `images_opentopia` | OpenTopia (defunct, mirrors Windy) | (use Windy) |
| 607    | `live-image_panomax` | Panomax webcam network | panomax.com |
| 569    | `i-traffic` (www.i-traffic.co.za) | South Africa i-Traffic | i-traffic.co.za |
| 561    | `weathercam_digitraffic` | Finland Digitraffic weathercams | digitraffic.fi |
| 547    | `micamerasimages` | Various Meteo camera networks | per-host lookup |
| 506    | `cctv_jogjaprov` | Indonesia Yogyakarta CCTV | jogjaprov.go.id |
| 459    | `imageserver_webcamera_pl` | Poland webcamera.pl | webcamera.pl |
| 435    | `public_carsprogram` (MN, Ireland) | US/Carsprogram regional traffic | carsprogram.org |
| 432    | `cctv_travelmidwest` (IL) | Illinois DOT via travelmidwest | travelmidwest.com |
| 432    | `feratel_*` (≈580 cams from wtvpict.feratel.com) | Feratel (Austrian tourism webcams) | feratel.com / opendatahub.bz.it |
| 235    | `iframe-extract` (incl. trafficcams.vancouver.ca, airportview.net) | Various iframe-extracted traffic/scenic cams | per-URL |
| 233    | `ireland_cr_IE` | Ireland TII traffic | tii.ie |
| 135    | `pl_webcamera_pl` | Poland webcamera.pl | webcamera.pl |
| 133    | `flood` (qldtraffic.qld.gov.au) | Queensland flood cams | qldtraffic.qld.gov.au |
| 131    | `japan_nexco` | Japan expressway NEXCO | drivetraffic.jp |
| 130    | `phenocam_NEON` | NEON phenocam science network | phenocam.nau.edu |
| 126    | `nysm` (api.nysmesonet.org) | NY State Mesonet | nysmesonet.org |
| 125    | `catalonia_cameres` (mct.gencat.cat) | Catalonia traffic | gencat.cat |
| 88     | `aero_cam_aero` (cam-aero.eu) | European aviation webcams | cam-aero.eu |
| 83     | `buoycam_ndbc` | NOAA NDBC buoy cams | ndbc.noaa.gov |
| 78     | `webcams_chmi` (intranet.chmi.cz) | Czech Hydromet Institute | chmi.cz |
| 78     | `autoroute_webcam_autoroute` (webcam-autoroute.eu) | French autoroute webcams | autoroute webcams |
| 73     | `tenerife_cic_tenerife_2701002` | Tenerife traffic | cic.tenerife.es |
| 57     | `sk_kukaj_sk` | Slovakia webcams (kukaj.profi-net.sk) | profi-net.sk |

**98.3% of all argus cams are either Windy (≈24.5%) or come from a state DOT / national road authority / meteo agency / open-data platform that publishes a public catalog with named cams.**

## 4. STRATEGY FOR CLEANUP

### Step 1 — Parse `notes` for `argus_id` and route by source

Create a per-row `argus_source` field. Match against a hard-coded map of source → strategy.

### Step 2 — Per-source enrichment (in priority order)

#### A. **Windy** (14,698 cams) — biggest win
- The URL pattern `https://imgproxy.windy.com/_/full/plain/current/<UUID>/original.jpg` contains a UUID
- Reverse-lookup strategy:
  1. Try `https://www.windy.com/-Webcams/webcams?UUID=<uuid>` — gives human-readable name + lat/lon + region
  2. Or use Windy's own REST endpoint `https://api.windy.com/webcams/v2/list?uuid=<uuid>` (if API key available — otherwise scrape)
  3. Or use Windy's public map GeoJSON at `https://www.windy.com/-Webcams/webcams` → search for the UUID in the page
- **Expected yield: ~100% name + city + lat/lon** (Windy maintains a rich public catalog)
- **Road name ("via"):** Windy gives locality name (city/POI), but not the street. For road-level, you'd need to reverse-geocode the lat/lon with Nominatim/OSM

#### B. **Japan MLIT River Cams** (9,086 cams) — second biggest
- URL pattern: `https://cam.river.go.jp:443` (image URLs are per-camera)
- The `argus_id` is `opencctv_cam_river_cam_river-<basin_id>` — the basin ID maps to a river system
- Reverse-lookup: `https://cam.river.go.jp/siteinfo/<basin_code>.html` returns the cam name (e.g. "Niyodo River - Ino")
- **Expected yield: 100% name + river + city** from the official site
- **Road name:** these are river-side, not road-side — use the river name as the "via"

#### C. **US State DOT traffic cams** (~6,000 cams across CA, MN, UT, IA, NV, IL, NY, LA, DE, FL)
- These all have public 511 sites with searchable cam catalogs:
  - CA: `wzmedia.dot.ca.gov` → https://quickmap.dot.ca.gov (cam name includes freeway + cross-street, e.g. "I-5 at I-405")
  - MN: `video.dot.state.mn.us` → https://511mn.org (cam name = "Hwy X at Y")
  - UT: `prod-ut.ibi511.com` → https://udot.iteris-cars.org (cam name = "I-15 at 12300 South")
  - IA: `atmsqf.iowadot.gov` → https://ia.carsprogram.org (cam name = "I-80 EB at Rest Area MM 159")
  - NV: `www.nvroads.com` → https://www.nvroads.com (cam name = "I-15 at MM 45")
  - IL: `cctv.travelmidwest.com` → cam name in URL e.g. `IL-DUPAGECOUNTY_1_DuPage_SB_Naper_4179610_-8811910_1_W.jpg` (lat/lon embedded!)
  - NY: `s52.nysdot.skyvdn.com` + `511ny.org` → cam name in `rtplive/R1_033/playlist.m3u8` (R1-033 = Route 1 camera 33)
- **Strategy:** the argus_id suffix often directly contains the cam number. Many hosts have a JSON/XML catalog:
  - `https://511ny.org/api/cams?bbox=...`
  - `https://www.dot.state.mn.us/cameras/...`
- **Expected yield: 100% name + lat/lon + road name** — these are PUBLIC cams, the DOTs WANT them found

#### D. **Spain DGT traffic cams** (1,769 cams)
- `etraffic.dgt.es` → https://infocar.dgt.es/etraffic/ (public DGT map)
- Cam names include road + PK (kilometer marker) e.g. "A-6 km 142"
- **Expected yield: 100% name + road + lat/lon** via DGT open data

#### E. **Avamet Spain meteo cams** (~250 cams)
- URL path `/estacions/<meteo_id>/<webcam>.jpg` — the meteo_id maps to a weather station
- `https://www.avamet.es/estacions/<id>` returns the station name, town, elevation
- **Expected yield: 100% town + station name**

#### F. **Italy Autostrade** (361 cams)
- `video.autostrade.it` — A1/A4/A22 etc. Italian motorway cams
- argus_id `opencctv_autostrade_autostrade-<n>` — the n is the cam ID
- Public list at https://autostrade.it/webcam (cam name = "A1 Milano-Napoli km 234" + lat/lon)
- **Expected yield: 100% name + motorway + km + lat/lon**

#### G. **Finland Digitraffic** (561 cams)
- `weathercam.digitraffic.fi` → https://www.digitraffic.fi/en/road-traffic/weathercams/
- JSON API: `https://www.digitraffic.fi/api/v1/road-monitoring/weathercams/<id>` (id is in the URL path)
- Returns: name, lat, lon, municipality, road, direction
- **Expected yield: 100% — best public API of the lot**

#### H. **South Africa i-Traffic** (569 cams)
- `www.i-traffic.co.za` → https://www.i-traffic.co.za (Cape Town/JHB cams)
- Cam name = "N1 at Rivonia" etc.

#### I. **Panomax** (607 cams)
- `live-image.panomax.com` → https://www.panomax.com (worldwide tourism cams, Austria/Switzerland heavy)
- Public site has cam pages with names and lat/lon

#### J. **Feratel / opendatahub** (~580 cams)
- `wtvpict.feratel.com`, `wtvthmb.feratel.com` → South Tyrol (Südtirol) tourism webcams
- argus_id embeds the Feratel UUID → public at https://www.suedtirol.info or https://www.feratel.com
- URL pattern: `?dcsdesign=WTP_opendatahubsuedtirol` — these come from the OpenDataHub Südtirol
- Direct catalog: `https://tourism.api.opendatahub.bz.it/v1/WeatherLivecam?` (public API, no key)

#### K. **Poland webcamera.pl** (459 cams)
- `imageserver.webcamera.pl/miniaturki/<town>.jpg` — **THE TOWN NAME IS IN THE URL!**
- This is the easiest cleanup — just regex the filename
- Example: `andrychow.jpg` → "Andrychów, Poland"
- **Expected yield: 100% from URL alone — no API needed**

#### L. **NOAA NDBC buoy cams** (83 cams)
- URL pattern: `https://www.ndbc.noaa.gov/.../<station_id>.jpg`
- The station_id maps to a named buoy station: https://www.ndbc.noaa.gov/station_page.php?station=<id>

#### M. **CCTV traffic (Hong Kong, Vietnam, Indonesia, China, Korea, Japan NEXCO, Tenerife)**
- All have government/open-data APIs with cam names + lat/lon
- Hong Kong: `tdcctv.data.one.gov.hk` → https://data.gov.hk
- Vietnam: `giaothong.hochiminhcity.gov.vn` → public HCMC traffic site
- Japan NEXCO: `cdn-livecamera-pic.drivetraffic.jp` → https://www.drivetraffic.jp/camera/

### Step 3 — Generic "cameras.alertcalifornia.org" / "i-traffic" / "imgproxy" / unidentified cams

For ~10,000 cams where source isn't easily mappable, fall back to:
1. **Lat/lon reverse geocoding** via Nominatim (OSM) → nearest road, neighborhood, city
2. **For the image proxy cams** (`imgproxy.windy.com` / `images-webcams.windy.com`) — match the UUID to Windy (above)
3. **For alertcalifornia.org** — these are the ALERTCalifornia wildfire network, ~200 named peaks (HerdPeak, OakCanyon, MiamiPeak, etc. — visible in the URL path). The argus_id `alertca-NNN` is the camera ID in the ALERTCalifornia catalog
4. **For unknown / no-lat cams** — if lat/lon is missing or default, mark `confidence=low` and skip

### Step 4 — Road name ("via") enrichment

After name + lat/lon are set, do a Nominatim reverse-geocode with `zoom=18` to get the nearest road/street. Example:
```
GET https://nominatim.openstreetmap.org/reverse?lat=-1.4&lon=35.0&format=json&zoom=18
→ {"address": {"road": "Mara River", ...}}
```
For traffic cams, the road is often a freeway/route — also include the route number from the cam name (e.g. "I-5", "A-6", "R-1", "Hwy 99").

**Rate-limit warning:** Nominatim allows 1 req/sec. With 60k cams, that's ~16 hours. Use a local Nominatim mirror or pay for a commercial API (Google/HERE/Mapbox).

## 5. EXPECTED COVERAGE

| Tier | Source | Count | Cleanup method | Yield |
|------|--------|------:|----------------|-------|
| Tier 1 (95–100%) | Windy (14,698), Japan MLIT (9,086), State DOTs US (~6,000), Spain DGT (1,769), Avamet (~250), Autostrade IT (361), Finland Digitraffic (561), Panomax (607), Feratel/Südtirol (~580), webcamera.pl PL (459), NOAA NDBC (83), Tenerife (73), I-Traffic ZA (569) | ~35,000 | Public API/catalog reverse-lookup | Full name + city + lat/lon + road |
| Tier 2 (60–90%) | Generic alertcalifornia (≈1,500), windy providers (≈5,000), state 511 misc (≈3,000) | ~10,000 | URL path parsing + reverse geocode | Name + city + lat/lon (no specific road) |
| Tier 3 (40–60%) | Misc meteo hosts (avametnuvol, gotafreda, catimenu, meteobunyol, etc.) | ~8,000 | Host name → Spanish/European town lookup + reverse geocode | City only |
| Tier 4 (low) | Truly anonymous (cameras.*, raw image proxies with no metadata) | ~6,000 | Pure reverse geocode to nearest POI | Generic area only |

**Total expected: ~50,000 of 59,938 cams can be enriched to at least (city, country, lat/lon, road name). The remaining ~10,000 will require manual triage or be marked as low-confidence.**

## 6. RECOMMENDED EXECUTION ORDER

1. **Build the `argus_source` classifier** — parse `notes`, bucket by source prefix (1 hour of code)
2. **Implement per-source enrichment modules** in priority order (Windy → Japan MLIT → State DOTs → Europe public APIs)
3. **Run reverse geocoding** as a backstop for any un-enriched cam (use a local Nominatim instance to avoid rate limits)
4. **Strip "(argus)" from `project_name`** as a final pass
5. **Update confidence scores** based on source reliability (Windy=high, generic=Nominatim-only=low)

## 7. KEY URLS TO BOOKMARK

- Windy webcam catalog: https://www.windy.com/-Webcams/webcams
- Finland Digitraffic API: https://www.digitraffic.fi/en/road-traffic/weathercams/
- Italy Autostrade: https://autostrade.it/autostrade-web/webcam
- South Tyrol OpenDataHub: https://tourism.api.opendatahub.bz.it/v1/WeatherLivecam
- Spain DGT: https://infocar.dgt.es/etraffic/
- California 511: https://quickmap.dot.ca.gov
- Iowa DOT 511: https://ia.carsprogram.org
- Utah 511: https://www.udot.utah.gov/connect/
- Poland webcamera.pl: https://webcamera.pl
- Panomax: https://www.panomax.com
- Cam.river.go.jp (Japan): https://cam.river.go.jp
- Nominatim reverse: https://nominatim.openstreetmap.org/reverse
- ALERTCalifornia: https://alertcalifornia.org
- Hong Kong TDCCTV: https://data.gov.hk/en-datasets/resource/hk-dgtmsd-td-cam-images
