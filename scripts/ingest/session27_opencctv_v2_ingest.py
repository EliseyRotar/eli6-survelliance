"""Ingest OpenCCTV v2 (Europe high-yield)."""
import csv, json
from pathlib import Path

CSV_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')
TEMP_DIR = Path(r'C:\Users\eli6-admin\AppData\Local\Temp\opencode')

with open(CSV_PATH, encoding='utf-8', newline='') as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = list(reader)
max_idx = max((int(r[0]) for r in rows if r[0].isdigit()), default=0)

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

src = TEMP_DIR / 'opencctv_eu_v2.json'
with open(src, encoding='utf-8') as f:
    oc_cams = json.load(f)
print(f"Loaded {len(oc_cams)} OpenCCTV v2 cams")

new_rows = []
idx = max_idx + 1
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
        str(idx), f"OCCTV {name[:80]}",
        f"https://www.opencctv.org/cameras/{cid}", live, cam_type,
        "False", "", "", "True", "live", "200",
        "video/mp4" if cam_type in ('hls', 'mp4') else "image/jpeg",
        "", name[:200],
        f"OpenCCTV public cam - {description or name} ({source or 'unknown'})",
        category, "Public camera", "OpenCCTV", model_str,
        country_full, state, city, "", address,
        "", "",
        f"{lat:.6f}" if lat else "", f"{lng:.6f}" if lng else "",
        "opencctv_official", source or "OpenCCTV.org", f"OpenCCTV ({country_code})",
        "", "", "www.opencctv.org",
        "high" if cam_type != 'image' else "medium",
        f"opencctv_id={cid}; source={source}; country={country_code}; direction={direction}; update_rate_ms={update_rate}",
        f"occtv_{cid[:60]}",
    ]
    if len(row) != 37:
        print(f"DEBUG len={len(row)}: {[v[:40] for v in row]}")
        assert False
    new_rows.append(row)
    idx += 1

print(f"Added {video_added} video + {static_added} static ({skipped} skipped)")
print(f"Total: {len(new_rows)}, new max idx: {idx - 1}")

with open(CSV_PATH, 'a', encoding='utf-8', newline='') as f:
    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
    for row in new_rows:
        writer.writerow(row)
print(f"Appended to {CSV_PATH}")
