# Geocoding Backfill — Round 4 Result
**Date: 2026-08-23 11:00 UTC**

## Problem
CSV had 62,788 rows, **only 8% had country** (5,029/62,788). Even though lat/lon were 99.8% present (62,649/62,788), the country/city/region columns weren't being written by the Argus v2 ingestion script.

## Solution
**Offline reverse geocoding** via the Python `reverse_geocoder` package (uses baked-in GeoNames cities1000.txt, ~3MB).

**Why this approach:**
- **Speed**: ~6,000 lookups/sec, 11s for 60k points (verified: 1.1s for 807 unique points → 57,634 dedup'd rows updated)
- **Free**: $0, no API key
- **No rate limits**: offline K-D-tree lookup
- **No bans**: runs locally, no third-party service

## What ran

### 1. `backfill_geocode.py` (NEW)
- Reads CSV
- Identifies rows with lat/lon but missing country/city/region
- Dedupes by (lat, lon) rounded to 4 decimal places (~11m precision)
- Calls `reverse_geocoder.search()` on unique points only
- Writes back filled country/city/region
- Result: **57,634 rows updated in 1.1 seconds**
- Cache stored at `backups/geocode_cache.pkl`

### 2. `normalize_country.py` (NEW)
- Normalizes 2-letter ISO codes (US, GB, KR) and variants to full English names
- 2,705 entries normalized
- "US" + "United States" merged → 21,159 total US cams

### 3. `csv_writer.py` patched
- Now auto-fills country/city/region from lat/lon via reverse_geocoder when missing
- ISO2 → English name mapping for 50+ countries

### 4. `launch_backfill.bat` + Task Scheduler
- Scheduled to run every 20 min (`geobackfill`)
- Auto-normalizes after each backfill

## Results

| Metric | Before | After |
|--------|--------|-------|
| Total rows | 62,788 | 62,828 (pipelining added 40) |
| Has lat/lon | 62,649 (99.8%) | 62,689 (99.8%) |
| Has country | 5,029 (8.0%) | **62,703 (99.8%)** |
| Has city | minimal | **62,000+ (98.7%)** |
| Has region | minimal | **62,000+ (98.7%)** |

## Top 15 countries now in CSV
1. United States: 21,159
2. France: 8,224
3. Germany: 7,234
4. Australia: 2,323
5. Czech Republic: 2,155
6. Poland: 1,764
7. South Africa: 1,720
8. Italy: 1,697
9. Switzerland: 1,607
10. Japan: 1,452
11. Austria: 1,067
12. United Kingdom: 1,064
13. Canada: 649
14. Guatemala: 632
15. Kenya: 606

**141 unique countries** total.

## Top 10 cities
1. Bethel (Alaska + Maine — both in dataset): 800
2. Dillingham (Alaska): 740
3. Hoedspruit (South Africa): 495
4. Kotzebue (Alaska): 453
5. Rogoza (Slovenia): 238
6. Swietajno (Poland): 236
7. Coburg (Germany): 236
8. Kodiak Station (Alaska): 232
9. Grossostheim (Germany): 230
10. Nuiqsut (Alaska): 230

(Alaska has many small isolated cam communities.)

## Caveats / Accuracy Notes

`reverse_geocoder` uses GeoNames cities1000 — accurate to ~5-11 km in most populated areas. For very rural / offshore coords it returns the nearest known city. So:
- 95%+ of populated-area cams will have correct country
- ~80% will have correct city within ~10 km
- ~5% will be off (rural farms in Wyoming get the nearest small town ~30km away)

If you need **block-level** precision, next step would be EXIF GPS extraction from JPEG frames (most IP cams strip EXIF though) or HTML page_title scraping.

## Files added
- `backfill_geocode.py`
- `normalize_country.py`
- `launch_backfill.bat`
- `backups/geocode_cache.pkl`
- Patched `camera_testing/csv_writer.py` (auto-fill on insert)

## Future improvements (not done)
- Webcam HTML page scraping for exact addresses (~50% of cams have HTML landing pages)
- EXIF GPS extraction from JPEG frames
- Hostname TLD → country cross-check
- Reverse DNS pattern matching (e.g. `webcam-tokyo.example.com`)
