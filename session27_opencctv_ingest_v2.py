"""
PHASE 3D: OpenCCTV Ingestion (FIXED with 37 columns)

Adds the 5,311 verified-live US video streams (HLS/MP4/MJPEG/iframe) + 14,689 static
image streams. Source: https://www.opencctv.org/

For video streams (m3u8, mp4, mjpeg, iframe) -> use the actual live URL
For image streams -> use the image URL
"""
import csv, json
from pathlib import Path

CSV_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')
TEMP_DIR = Path(r'C:\Users\eli6-admin\AppData\Local\Temp\opencode')

# Find max idx
with open(CSV_PATH, encoding='utf-8', newline='') as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = list(reader)
max_idx = max((int(r[0]) for r in rows if r[0].isdigit()), default=0)
start_idx = max_idx + 1
print(f"Current max idx: {max_idx}")
print(f"Adding OpenCCTV cams starting at {start_idx}")
print(f"Header cols: {len(header)}")

# Load OpenCCTV US data
oc_path = TEMP_DIR / 'opencctv_us_all.json'
if not oc_path.exists():
    print(f"ERROR: {oc_path} not found. Run fetch_opencctv_all.py first.")
    exit(1)

with open(oc_path, encoding='utf-8') as f:
    oc_cams = json.load(f)
print(f"Loaded {len(oc_cams)} OpenCCTV US cams")

def s(v):
    return (v or '').strip() if v else ''

# Build new rows
new_rows = []
idx = start_idx
video_added = 0
static_added = 0
skipped = 0

for c in oc_cams:
    if not c.get('id'):
        skipped += 1
        continue
    feed_type = c.get('feed_type', 'image')
    feed_url = c.get('feed_url', '')
    if not feed_url:
        skipped += 1
        continue
    cid = c.get('id', '')
    name = s(c.get('name')) or f'OpenCCTV {cid}'
    city = s(c.get('city'))
    state = s(c.get('state'))
    country = s(c.get('country'))
    lat = c.get('lat')
    lng = c.get('lng')
    category = s(c.get('category')) or 'traffic'
    source = s(c.get('source'))
    direction = s(c.get('direction'))
    update_rate = c.get('update_rate')
    description = s(c.get('description'))

    # Map feed_type to our type
    if feed_type == 'm3u8':
        cam_type = 'hls'
        live = feed_url
        video_added += 1
    elif feed_type == 'mp4':
        cam_type = 'mp4'
        live = feed_url
        video_added += 1
    elif feed_type == 'mjpeg':
        cam_type = 'mp4'
        live = feed_url
        video_added += 1
    elif feed_type == 'iframe':
        cam_type = 'mp4'
        live = feed_url
        video_added += 1
    else:
        cam_type = 'image'
        live = feed_url
        static_added += 1

    # Build address
    addr_parts = []
    if direction and direction not in ('NONE', 'None', ''):
        addr_parts.append(direction)
    if city:
        addr_parts.append(city)
    if state:
        addr_parts.append(state)
    if country:
        addr_parts.append(country)
    address = ', '.join(addr_parts) if addr_parts else f"{country or 'Unknown'}"

    # Map country code to full name
    country_full = {'US': 'United States', 'GB': 'United Kingdom', 'CA': 'Canada',
                    'FR': 'France', 'DE': 'Germany', 'IT': 'Italy', 'ES': 'Spain',
                    'NL': 'Netherlands', 'JP': 'Japan', 'AU': 'Australia', 'NZ': 'New Zealand'}.get(country, country)
    # model describes the kind of camera
    model_str = f"OpenCCTV {feed_type}"

    row = [
        str(idx),                              # 0 idx
        f"OCCTV {name[:80]}",                  # 1 project_name
        f"https://www.opencctv.org/cameras/{cid}",  # 2 url
        live,                                  # 3 live_stream_url
        cam_type,                              # 4 type
        "False",                               # 5 auth_required
        "",                                    # 6 auth_user
        "",                                    # 7 auth_pass
        "True",                                # 8 enabled
        "live",                                # 9 live_status
        "200",                                 # 10 http_status
        "video/mp4" if cam_type in ('hls','mp4') else "image/jpeg",  # 11 content_type
        "",                                    # 12 server_header
        name[:200],                           # 13 page_title
        f"OpenCCTV public cam - {description or name} ({source or 'unknown'})",  # 14 description
        category,                              # 15 category
        "Public camera",                       # 16 likely_subject
        "OpenCCTV",                            # 17 brand
        model_str,                             # 18 model
        country_full,                          # 19 country
        state,                                 # 20 region
        city,                                  # 21 city
        "",                                    # 22 zip
        address,                               # 23 address
        "",                                    # 24 road
        "",                                    # 25 location_precision
        f"{lat:.6f}" if lat else "",            # 26 lat
        f"{lng:.6f}" if lng else "",            # 27 lon
        "opencctv_official",                   # 28 geo_source
        source or "OpenCCTV.org",               # 29 isp
        f"OpenCCTV ({country})",                # 30 org
        "",                                    # 31 asn
        "",                                    # 32 reverse_dns
        "www.opencctv.org",                    # 33 host
        "high" if video_added > 0 else "medium",  # 34 confidence
        f"opencctv_id={cid}; source={source}; direction={direction}; update_rate_ms={update_rate}",  # 35 notes
        f"occtv_{cid[:60]}",                   # 36 csv_id
    ]
    if len(row) != 37:
        print(f"DEBUG row len={len(row)}:")
        for i, v in enumerate(row):
            print(f"  [{i}] = {v[:60]!r}")
    assert len(row) == 37, f"OCCTV row has {len(row)} cols, expected 37"
    new_rows.append(row)
    idx += 1

print(f"Added {video_added} video + {static_added} static OpenCCTV cams ({skipped} skipped)")
print(f"Total new rows: {len(new_rows)}, new max idx: {idx - 1}")

# Write to CSV
with open(CSV_PATH, 'a', encoding='utf-8', newline='') as f:
    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
    for row in new_rows:
        writer.writerow(row)
print(f"Appended to {CSV_PATH}")
