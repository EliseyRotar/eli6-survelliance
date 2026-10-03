"""
Ingest 14 new kenyawebcam.com cams + 10 new Africam Kenya YouTube live cams
into the CSV. Uses mjpeg type for kenyawebcam (poll JPEGs every 3s) and
youtube type for Africam (YouTube iframe embed).
"""
import csv
import json
from pathlib import Path

CSV_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')
KW_CAMS_PATH = Path(r'C:\Users\eli6-admin\AppData\Local\Temp\opencode\kenyawebcam_cams.json')

# ----- Load parsed kenyawebcam cams -----
with open(KW_CAMS_PATH, encoding='utf-8') as f:
    kw_cams = json.load(f)

# ----- Read CSV to find existing slugs and max idx -----
with open(CSV_PATH, encoding='utf-8', newline='') as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = list(reader)

# Detect existing slugs (any kenyawebcam kenyawebcams domain match)
existing_slugs = set()
for row in rows:
    if not row[0].isdigit():
        continue
    combined = (row[1] if len(row) > 1 else '') + ' ' + (row[2] if len(row) > 2 else '') + ' ' + (row[3] if len(row) > 3 else '')
    for c in kw_cams:
        slug = c['slug']
        if f'/{slug}/' in combined and 'kenyawebcam' in combined.lower():
            existing_slugs.add(slug)
            break

print(f"Existing slugs in CSV: {len(existing_slugs)}")
new_kw = [c for c in kw_cams if c['slug'] not in existing_slugs]
print(f"New kenyawebcam cams to add: {len(new_kw)}")

# ----- Africam Kenya YouTube cams (verified via oEmbed) -----
AFRICAM_CAMS = [
    # (name, location, region, lat, lng, yt_id, description)
    ("Angama Amboseli Live Cam", "Amboseli, Kajiado", "Amboseli", -2.6527, 37.2606, "i12eS_2YV-s", "Angama Amboseli | Wildlife Beneath Kilimanjaro"),
    ("Porini Rhino Camp Live Cam", "Ol Pejeta Conservancy, Laikipia", "Ol Pejeta", 0.0024, 36.9302, "5dhmXmUD1ZE", "Porini Rhino Camp | Ol Pejeta Conservancy, Kenya"),
    ("Angama Mara Live Cam", "Maasai Mara, Narok", "Maasai Mara", -1.4061, 35.0117, "Njur5IV7icE", "Angama Mara | Maasai Mara, Kenya"),
    ("Mara River Fig Tree Live Cam", "Mara Triangle, Narok", "Mara Triangle", -1.4102, 35.0132, "ACc7IkdOF-Y", "Mara River LIVE: Fig Tree Crossing Wildebeest Migration Cam"),
    ("Mara River Main Crossing Live Cam", "Mara Triangle, Narok", "Mara Triangle", -1.4102, 35.0132, "BaEFc79IMCA", "LIVE: Mara River Main Crossing | Masai Mara Wildlife Cam 24/7"),
    ("Tortilis Camp Live Cam", "Amboseli, Kajiado", "Amboseli", -2.6841, 37.2495, "XyPU5-pNg5E", "Live from Tortilis Camp | Amboseli Waterhole with Mount Kilimanjaro"),
    ("Mahali Mzuri Waterhole Cam", "Maasai Mara, Narok", "Maasai Mara", -1.4050, 35.0092, "ZWhvO6R37ck", "Mahali Mzuri Lodge Live Cam | Maasai Mara, Kenya"),
    ("Mahali Mzuri Landscape Cam", "Maasai Mara, Narok", "Maasai Mara", -1.4050, 35.0092, "jIh2FYqMOw0", "Mahali Mzuri Landscape Live Cam | Maasai Mara, Kenya"),
    ("Finch Hattons Live Cam", "Tsavo West, Taita Taveta", "Tsavo West", -2.9876, 38.4672, "Xe9CPAdyAro", "Finch Hattons Live Wildlife Camera | Tsavo National Park"),
    ("Lentorre Lodge Live Cam", "South Central Rift Valley", "Rift Valley", -0.8166, 36.2763, "bEmFpjwMOvs", "Live From Lentorre, Kenya | Live Wildlife Camera"),
]
print(f"New Africam YouTube cams to add: {len(AFRICAM_CAMS)}")

# ----- Find max idx -----
max_idx = max((int(r[0]) for r in rows if r[0].isdigit()), default=0)
start_idx = max_idx + 1
print(f"Current max idx: {max_idx}, adding rows starting at {start_idx}")

# ----- Build new rows -----
new_rows = []
idx = start_idx

# 1) Kenyawebcam mjpeg cams
for c in new_kw:
    slug = c['slug']
    domain = c['domain']
    url_type = c['url_type']
    url = f"https://{domain}/{slug}/pic/{url_type}.jpg"
    name = c['location']  # e.g. "Nairobi ESE" or "Wilson Airport"
    region = c['region']
    lat = c['lat']
    lng = c['lng']
    geo_source = c.get('geo_source', 'approximated_from_region')
    direction = c.get('direction', '')
    altitude = c.get('altitude_ft', 0)
    location_label = c.get('location', '')

    row = [
        str(idx),
        f"Kenyawebcam {name} ({slug})",
        "https://webcams.aeroclubea.com/",  # homepage reference
        url,
        "mjpeg",
        "False", "", "",
        "True", "live", "200", "image/jpeg",
        "",  # server_header
        f"Kenyawebcam.com {region} - {location_label}",
        f"Kenyawebcam.com live image (refreshed every 3-15min by camera uploader). Direction: {direction}. Altitude: {altitude} ft. Original source: https://webcams.aeroclubea.com/ hosted by Aero Club of East Africa.",
        "scenic", "Live public camera",
        "Aero Club of East Africa", "Webcam network",
        "Kenya", region,
        location_label.split(' - ')[0] if ' - ' in location_label else location_label,
        "",  # zip
        f"{region}, Kenya",
        f"{lat:.6f}", f"{lng:.6f}",
        geo_source,
        "Aero Club of East Africa",
        f"Kenyawebcam.com ({region})",
        "",  # asn
        "",  # reverse_dns
        domain,
        "medium" if geo_source == "approximated_from_region" else "high",
        f"kenyawebcam_id={slug}; type={url_type}; direction={direction}; altitude_ft={altitude}; original_name={name}",
        f"kenyawebcam_{slug}",
    ]
    new_rows.append(row)
    idx += 1

# 2) Africam Kenya YouTube live cams
for name, loc, region, lat, lng, yt_id, desc in AFRICAM_CAMS:
    yt_url = f"https://www.youtube.com/watch?v={yt_id}"
    row = [
        str(idx),
        f"Africam {name}",
        yt_url,  # homepage
        yt_url,  # live_stream_url
        "youtube",  # type
        "False", "", "",
        "True", "live", "200", "text/html; charset=utf-8",
        "",  # server_header
        desc,
        f"Africam.com YouTube live stream - {region}, Kenya. {desc}",
        "scenic", "Live public camera",
        "Africam", "Wildlife live stream",
        "Kenya", region,
        loc.split(',')[0].strip(),  # city
        "",  # zip
        f"{loc}, Kenya",
        f"{lat:.6f}", f"{lng:.6f}",
        "africa_wildlife_gis",
        "Africam (WildEarth)",
        f"Africam ({region})",
        "", "", "youtube.com",
        "high",
        f"africam_lodge={region}; yt_id={yt_id}; yt_title={desc}",
        f"africam_{yt_id}",
    ]
    new_rows.append(row)
    idx += 1

# ----- Append to CSV -----
with open(CSV_PATH, 'a', encoding='utf-8', newline='') as f:
    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
    for row in new_rows:
        writer.writerow(row)

print(f"\nAppended {len(new_rows)} rows. New max idx: {idx - 1}")
print(f"  - {len(new_kw)} new kenyawebcam mjpeg cams")
print(f"  - {len(AFRICAM_CAMS)} new Africam YouTube cams")
