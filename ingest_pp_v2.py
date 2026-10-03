"""Ingest 90 new Pet Paradise cams discovered via abckam portal scraping."""
import json, csv, sys
sys.stdout = open(sys.stdout.fileno(), 'w', encoding='utf-8')
from pathlib import Path
import re, shutil, datetime

src = Path(r'C:\Users\eli6-admin\AppData\Local\Temp\pp_new_streams.json')
csv_path = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')

with src.open(encoding='utf-8') as f:
    new_streams = json.load(f)
print(f'New streams to ingest: {len(new_streams)}')

# Build location → city/state lookup from PP website
LOC_INFO = {
    # Alabama
    'petparadisebirmingham': ('Birmingham', 'Alabama', '33.5186', '-86.8104'),
    'petparadisecliftfarm': ('Madison', 'Alabama', '34.7567', '-86.7485'),
    # Arizona
    'petparadisephoenix': ('Phoenix', 'Arizona', '33.7123', '-112.0953'),
    # Florida
    'petparadiseamelia': ('Yulee', 'Florida', '30.6311', '-81.5826'),
    'petparadiseapollobeach': ('Apollo Beach', 'Florida', '27.7661', '-82.3841'),
    'petparadisebartram': ('Jacksonville', 'Florida', '30.1049', '-81.4836'),
    'petparadisebonitasprings': ('Bonita Springs', 'Florida', '26.3874', '-81.8079'),
    'petparadisecoconutcreek': ('Coconut Creek', 'Florida', '26.3183', '-80.1822'),
    'petparadisefleming': ('Fleming Island', 'Florida', '30.0683', '-81.7092'),
    'petparadiseftlauderdale': ('Davie', 'Florida', '26.0658', '-80.2854'),
    'petparadiseftmyers': ('San Carlos Park', 'Florida', '26.4927', '-81.8421'),
    'petparadisegainesville': ('Newberry', 'Florida', '29.6557', '-82.5499'),
    'petparadisejaxairport': ('Jacksonville', 'Florida', '30.4957', '-81.6700'),
    'petparadiseuniversity': ('Jacksonville', 'Florida', '30.2665', '-81.6141'),
    'petparadiselakebuenavista': ('Orlando', 'Florida', '28.4021', '-81.4860'),
    'petparadiselakenona': ('Orlando', 'Florida', '28.3800', '-81.2200'),
    'petparadiselakewoodranch': ('Bradenton', 'Florida', '27.4750', '-82.4100'),
    'petparadisenaples': ('Naples', 'Florida', '26.2100', '-81.8000'),
    'petparadiseoakleaf': ('Middleburg', 'Florida', '30.0700', '-81.8500'),
    'petparadiseocala': ('Ocala', 'Florida', '29.0849', '-82.1400'),
    'petparadiseodessa': ('Odessa', 'Florida', '28.1500', '-82.5800'),
    'petparadiseormondbeach': ('Ormond Beach', 'Florida', '29.2858', '-81.0559'),
    'petparadisepalmbeach': ('West Palm Beach', 'Florida', '26.7153', '-80.0534'),
    'petparadisepalmcoast': ('Bunnell', 'Florida', '29.4666', '-81.2567'),
    'petparadisesanford': ('Sanford', 'Florida', '28.7995', '-81.2756'),
    'petparadisestaugustine': ('St. Augustine', 'Florida', '29.8946', '-81.3145'),
    'petparadiseworldgolfvillage': ('St Augustine', 'Florida', '29.9900', '-81.4500'),
    'petparadisetallahassee': ('Tallahassee', 'Florida', '30.4717', '-84.2697'),
    'petparadiseviera': ('Rockledge', 'Florida', '28.2343', '-80.7225'),
    'petparadisewesleychapel': ('Wesley Chapel', 'Florida', '28.2500', '-82.3500'),
    'petparadiseocoee': ('Winter Garden', 'Florida', '28.5653', '-81.5861'),
    # Georgia
    'petparadiseatlantaairport': ('College Park', 'Georgia', '33.6407', '-84.4497'),
    'petparadiselawrenceville': ('Lawrenceville', 'Georgia', '33.9562', '-83.9880'),
    'petparadisepeachtreecity': ('Sharpsburg', 'Georgia', '33.4012', '-84.6507'),
    'petparadisepooler': ('Pooler', 'Georgia', '32.1154', '-81.2470'),
    'petparadisesnellville': ('Snellville', 'Georgia', '33.8573', '-84.0199'),
    'petparadisewoodstock': ('Woodstock', 'Georgia', '34.1015', '-84.5194'),
    # North Carolina
    'petparadisecary': ('Apex', 'North Carolina', '35.7326', '-78.8503'),
    'petparadisecharlotteairport': ('Charlotte', 'North Carolina', '35.2137', '-80.9430'),
    'petparadiselakenorman': ('Huntersville', 'North Carolina', '35.4107', '-80.8595'),
    'petparadisematthews': ('Matthews', 'North Carolina', '35.1168', '-80.7237'),
    'petparadisemooresville': ('Mooresville', 'North Carolina', '35.5849', '-80.8101'),
    'petparadisewilmington': ('Wilmington', 'North Carolina', '34.2257', '-77.9447'),
    # South Carolina
    'petparadiseballantyne': ('Indian Land', 'South Carolina', '34.9918', '-80.8501'),
    'petparadisecolumbia': ('Columbia', 'South Carolina', '34.0007', '-81.0348'),
    'petparadisegreenville': ('Greenville', 'South Carolina', '34.8526', '-82.3940'),
    'petparadisehiltonhead': ('Okatie', 'South Carolina', '32.3007', '-80.9484'),
    # Tennessee
    'petparadisechattanooga': ('Collegedale', 'Tennessee', '35.0535', '-85.0500'),
    'petparadisemurfreesboro': ('Murfreesboro', 'Tennessee', '35.8456', '-86.3903'),
    # Texas
    'petparadisecedarpark': ('Cedar Park', 'Texas', '30.5052', '-97.8203'),
    'petparadisedrippingsprings': ('Austin', 'Texas', '30.1900', '-98.0400'),
    'petparadisegeorgetown': ('Georgetown', 'Texas', '30.6332', '-97.6779'),
    'petparadisehoustonhobby': ('Houston', 'Texas', '29.6469', '-95.2817'),
    'petparadisehoustoniahnorth': ('Houston', 'Texas', '29.9994', '-95.3500'),
    'petparadisekyle': ('Kyle', 'Texas', '29.9894', '-97.8775'),
    'petparadiselascolinas': ('Irving', 'Texas', '32.8927', '-96.9650'),
    'petparadiseplanocuster': ('Plano', 'Texas', '33.0198', '-96.7266'),
    'petparadiseplanopremier': ('Plano', 'Texas', '33.0500', '-96.7300'),
    'petparadisestoneoak': ('San Antonio', 'Texas', '29.6500', '-98.4500'),
    # Virginia
    'petparadisecharlottesville': ('Charlottesville', 'Virginia', '38.0293', '-78.4767'),
    'petparadisechesterfield': ('North Chesterfield', 'Virginia', '37.5038', '-77.5278'),
    'petparadiserichmondairport': ('Richmond', 'Virginia', '37.5025', '-77.3588'),
}

# Read CSV
with csv_path.open(encoding='utf-8', newline='') as f:
    rdr = csv.DictReader(f)
    fieldnames = rdr.fieldnames
    rows = list(rdr)
existing_urls = set(r.get('live_stream_url','') for r in rows)
existing_idxs = set(int(r['idx']) for r in rows if r.get('idx','').isdigit())
max_idx = max(existing_idxs)

new_rows = []
skipped = 0
for stream in new_streams:
    url = stream['stream']
    if url in existing_urls:
        skipped += 1
        continue

    portal_loc = stream['location']
    city, state, lat, lon = LOC_INFO.get(portal_loc, ('', '', '', ''))

    # Title: "abcKam.com : Pet Paradise : <Location> : <Cam Name>"
    title = stream.get('title','')
    m = re.search(r':\s*(?:Pet Paradise\s*:\s*)?(.*?)\s*:\s*(.+?)\s*$', title)
    if m:
        loc_name = m.group(1).strip()
        cam_name = m.group(2).strip()
    else:
        loc_name = portal_loc.replace('petparadise', '').replace('-', ' ').title()
        cam_name = title

    proj_name = f'Pet Paradise {loc_name} - {cam_name}'

    row = {
        'idx': str(max_idx + 1 + len(new_rows)),
        'live_stream_url': url,
        'project_name': proj_name[:200],
        'city': city,
        'region': state,
        'country': 'United States',
        'lat': lat,
        'lon': lon,
        'road': 'Pet Paradise',
        'location_precision': 'exact' if lat else 'region',
        'live_status': 'live',
        'enabled': '1',
        'host': re.sub(r'https?://([^/:]+).*', r'\1', url),
        'type': 'hls',
        'isp': 'abckam',
        'category': 'animal-care',
        'notes': f'Portal: {portal_loc} cam{stream["cam_n"]}, slug: {stream["slug"]}',
    }

    for fn in fieldnames:
        if fn not in row:
            row[fn] = ''
    new_rows.append(row)

print(f'\nNew rows to add: {len(new_rows)} Skipped: {skipped}')

# Backup
backup_name = f'backup_20260915_{datetime.datetime.now().strftime("%H%M%S")}_session38c'
backup_path = csv_path.parent / 'backups' / backup_name
backup_path.mkdir(parents=True, exist_ok=True)
shutil.copy2(csv_path, backup_path / csv_path.name)
print(f'Backed up to {backup_path}')

# Write
all_rows = rows + new_rows
with csv_path.open('w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(all_rows)
print(f'Wrote {len(all_rows)} rows (was {len(rows)})')

# Save script
shutil.copy2(Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\ingest_pp_v2.py'),
             backup_path / 'ingest_pp_v2.py')

# Sample
if new_rows:
    r0 = new_rows[0]
    print(f'\nSample new row:')
    for k in ['idx', 'project_name', 'city', 'region', 'live_stream_url']:
        print(f'  {k}: {str(r0.get(k,""))[:100]}')
