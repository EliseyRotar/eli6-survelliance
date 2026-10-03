"""Ingest OpenCCTV international + EU into CSV (skip if already present)."""
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
print(f"Current max idx: {max_idx}")
print(f"Header cols: {len(header)}")

# Get existing live URLs to dedupe
existing_live = set()
for r in rows:
    if len(r) > 3 and r[3]:
        existing_live.add(r[3])
print(f"Existing live URLs: {len(existing_live)}")

def s(v):
    return (v or '').strip() if v else ''

COUNTRY_FULL = {'US': 'United States', 'GB': 'United Kingdom', 'CA': 'Canada',
                'FR': 'France', 'DE': 'Germany', 'IT': 'Italy', 'ES': 'Spain',
                'NL': 'Netherlands', 'JP': 'Japan', 'AU': 'Australia', 'NZ': 'New Zealand',
                'BR': 'Brazil', 'PT': 'Portugal', 'GR': 'Greece', 'PL': 'Poland',
                'CZ': 'Czechia', 'HU': 'Hungary', 'RO': 'Romania', 'AT': 'Austria',
                'CH': 'Switzerland', 'BE': 'Belgium', 'IE': 'Ireland',
                'TR': 'Turkey', 'MX': 'Mexico', 'IN': 'India', 'RU': 'Russia'}

new_rows = []
idx = max_idx + 1
video_added = 0
static_added = 0
skipped = 0

# Load and process both files
for src in ['opencctv_intl.json', 'opencctv_eu.json']:
    p = TEMP_DIR / src
    if not p.exists():
        continue
    with open(p, encoding='utf-8') as f:
        oc_cams = json.load(f)
    print(f'\nProcessing {src}: {len(oc_cams)} cams')
    for c in oc_cams:
        if not c.get('id'):
            skipped += 1
            continue
        feed_type = c.get('feed_type', 'image')
        feed_url = c.get('feed_url', '')
        if not feed_url:
            skipped += 1
            continue
        # Dedupe
        if feed_url in existing_live:
            skipped += 1
            continue
        existing_live.add(feed_url)
        cid = c.get('id', '')
        name = s(c.get('name')) or f'OpenCCTV {cid}'
        city = s(c.get('city'))
        state = s(c.get('state'))
        country_code = s(c.get('country'))
        country_full = COUNTRY_FULL.get(country_code, country_code)
        lat = c.get('lat')
        lng = c.get('lng')
        category = s(c.get('category')) or 'traffic'
        source = s(c.get('source'))
        direction = s(c.get('direction'))
        update_rate = c.get('update_rate')
        description = s(c.get('description'))

        if feed_type == 'm3u8':
            cam_type = 'hls'
            live = feed_url
            video_added += 1
        elif feed_type in ('mp4', 'mjpeg', 'iframe'):
            cam_type = 'mp4'
            live = feed_url
            video_added += 1
        else:
            cam_type = 'image'
            live = feed_url
            static_added += 1

        addr_parts = []
        if direction and direction not in ('NONE', 'None', ''):
            addr_parts.append(direction)
        if city:
            addr_parts.append(city)
        if state:
            addr_parts.append(state)
        if country_full:
            addr_parts.append(country_full)
        address = ', '.join(addr_parts) if addr_parts else (country_full or 'Unknown')

        model_str = f"OpenCCTV {feed_type}"

        row = [
            str(idx),                                # 0 idx
            f"OCCTV {name[:80]}",                    # 1 project_name
            f"https://www.opencctv.org/cameras/{cid}",  # 2 url
            live,                                    # 3 live_stream_url
            cam_type,                                # 4 type
            "False",                                 # 5 auth_required
            "",                                      # 6 auth_user
            "",                                      # 7 auth_pass
            "True",                                  # 8 enabled
            "live",                                  # 9 live_status
            "200",                                   # 10 http_status
            "video/mp4" if cam_type in ('hls', 'mp4') else "image/jpeg",  # 11 content_type
            "",                                      # 12 server_header
            name[:200],                             # 13 page_title
            f"OpenCCTV public cam - {description or name} ({source or 'unknown'})",  # 14 description
            category,                                # 15 category
            "Public camera",                         # 16 likely_subject
            "OpenCCTV",                              # 17 brand
            model_str,                               # 18 model
            country_full,                            # 19 country
            state,                                   # 20 region
            city,                                    # 21 city
            "",                                      # 22 zip
            address,                                 # 23 address
            "",                                      # 24 road
            "",                                      # 25 location_precision
            f"{lat:.6f}" if lat else "",            # 26 lat
            f"{lng:.6f}" if lng else "",            # 27 lon
            "opencctv_official",                     # 28 geo_source
            source or "OpenCCTV.org",                # 29 isp
            f"OpenCCTV ({country_code})",            # 30 org
            "",                                      # 31 asn
            "",                                      # 32 reverse_dns
            "www.opencctv.org",                      # 33 host
            "high" if cam_type != 'image' else "medium",  # 34 confidence
            f"opencctv_id={cid}; source={source}; country={country_code}; direction={direction}; update_rate_ms={update_rate}",  # 35 notes
            f"occtv_{cid[:60]}",                     # 36 csv_id
        ]
        if len(row) != 37:
            print(f"DEBUG len={len(row)}")
            for i, v in enumerate(row):
                print(f"  [{i}] = {v[:60]!r}")
            assert False
        new_rows.append(row)
        idx += 1

print(f"\nAdded {video_added} video + {static_added} static ({skipped} skipped)")
print(f"Total new rows: {len(new_rows)}, new max idx: {idx - 1}")

# Write
with open(CSV_PATH, 'a', encoding='utf-8', newline='') as f:
    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
    for row in new_rows:
        writer.writerow(row)
print(f"Appended to {CSV_PATH}")
