"""
geo_rebuild_v4.py - Final cleanup pass:
  1. Map 2-letter country codes (IT, DE, GB, FI, FR, etc.) to full names
  2. Distribute autostrade.it cams across Italy by dt1-dt9 highway code
  3. Final stat dump
"""
import csv
import io
import json
import os
import re
import sys
import time
from collections import Counter
from urllib.parse import urlparse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

CSV_PATH = r"C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv"
TV_CATALOG = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\tv_catalog_full.json"
PROGRESS_PATH = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\geo_rebuild_v4_progress.json"

# 2-letter country code to full name
ISO2_TO_NAME = {
    'US': 'United States', 'CA': 'Canada', 'MX': 'Mexico', 'BR': 'Brazil',
    'AR': 'Argentina', 'CL': 'Chile', 'CO': 'Colombia', 'PE': 'Peru',
    'GB': 'United Kingdom', 'FR': 'France', 'DE': 'Germany', 'IT': 'Italy',
    'ES': 'Spain', 'PT': 'Portugal', 'NL': 'Netherlands', 'BE': 'Belgium',
    'AT': 'Austria', 'CH': 'Switzerland', 'SE': 'Sweden', 'NO': 'Norway',
    'FI': 'Finland', 'DK': 'Denmark', 'IE': 'Ireland', 'PL': 'Poland',
    'CZ': 'Czech Republic', 'SK': 'Slovakia', 'HU': 'Hungary', 'RO': 'Romania',
    'BG': 'Bulgaria', 'GR': 'Greece', 'HR': 'Croatia', 'SI': 'Slovenia',
    'RS': 'Serbia', 'BA': 'Bosnia and Herzegovina', 'MK': 'North Macedonia',
    'AL': 'Albania', 'ME': 'Montenegro', 'LT': 'Lithuania', 'LV': 'Latvia',
    'EE': 'Estonia', 'IS': 'Iceland', 'LU': 'Luxembourg', 'MT': 'Malta',
    'CY': 'Cyprus', 'TR': 'Turkey', 'RU': 'Russia', 'UA': 'Ukraine',
    'BY': 'Belarus', 'MD': 'Moldova', 'GE': 'Georgia', 'AM': 'Armenia',
    'AZ': 'Azerbaijan', 'KZ': 'Kazakhstan', 'UZ': 'Uzbekistan',
    'CN': 'China', 'JP': 'Japan', 'KR': 'South Korea', 'KP': 'North Korea',
    'MN': 'Mongolia', 'TW': 'Taiwan', 'HK': 'Hong Kong', 'MO': 'Macao',
    'IN': 'India', 'PK': 'Pakistan', 'BD': 'Bangladesh', 'LK': 'Sri Lanka',
    'NP': 'Nepal', 'BT': 'Bhutan', 'MV': 'Maldives', 'AF': 'Afghanistan',
    'IR': 'Iran', 'IQ': 'Iraq', 'SA': 'Saudi Arabia', 'AE': 'United Arab Emirates',
    'OM': 'Oman', 'YE': 'Yemen', 'JO': 'Jordan', 'LB': 'Lebanon', 'SY': 'Syria',
    'IL': 'Israel', 'PS': 'Palestine', 'KW': 'Kuwait', 'QA': 'Qatar', 'BH': 'Bahrain',
    'TH': 'Thailand', 'VN': 'Vietnam', 'MY': 'Malaysia', 'SG': 'Singapore',
    'ID': 'Indonesia', 'PH': 'Philippines', 'KH': 'Cambodia', 'LA': 'Laos',
    'MM': 'Myanmar', 'BN': 'Brunei', 'TL': 'Timor-Leste',
    'AU': 'Australia', 'NZ': 'New Zealand', 'PG': 'Papua New Guinea', 'FJ': 'Fiji',
    'EG': 'Egypt', 'LY': 'Libya', 'TN': 'Tunisia', 'DZ': 'Algeria', 'MA': 'Morocco',
    'ET': 'Ethiopia', 'KE': 'Kenya', 'TZ': 'Tanzania', 'UG': 'Uganda',
    'NG': 'Nigeria', 'GH': 'Ghana', 'SN': 'Senegal', 'CI': 'Cote d\'Ivoire',
    'CM': 'Cameroon', 'AO': 'Angola', 'ZM': 'Zambia', 'ZW': 'Zimbabwe',
    'BW': 'Botswana', 'NA': 'Namibia', 'ZA': 'South Africa', 'MU': 'Mauritius',
    'MG': 'Madagascar', 'CD': 'Democratic Republic of the Congo', 'CG': 'Congo',
    'CR': 'Costa Rica', 'PA': 'Panama', 'GT': 'Guatemala', 'HN': 'Honduras',
    'SV': 'El Salvador', 'NI': 'Nicaragua', 'CU': 'Cuba', 'DO': 'Dominican Republic',
    'HT': 'Haiti', 'JM': 'Jamaica', 'PR': 'Puerto Rico', 'TT': 'Trinidad and Tobago',
    'BS': 'Bahamas', 'BB': 'Barbados', 'GD': 'Grenada', 'LC': 'Saint Lucia',
    'AG': 'Antigua and Barbuda', 'DM': 'Dominica', 'VC': 'Saint Vincent and the Grenadines',
    'KY': 'Cayman Islands', 'VG': 'British Virgin Islands', 'VI': 'US Virgin Islands',
    'BM': 'Bermuda', 'GL': 'Greenland', 'IS': 'Iceland', 'FO': 'Faroe Islands',
    'SJ': 'Svalbard and Jan Mayen', 'AX': 'Aland Islands', 'LI': 'Liechtenstein',
    'AD': 'Andorra', 'MC': 'Monaco', 'SM': 'San Marino', 'VA': 'Vatican City',
    'XK': 'Kosovo', 'GE': 'Georgia', 'AM': 'Armenia', 'AZ': 'Azerbaijan',
    'MN': 'Mongolia',
}

# Autostrade highway dt -> approximate center (lat, lon)
# These are the major Italian autostrade A1-A9 mapped to dt1-dt9
AUTOSTRADE_HIGHWAYS = {
    'dt1': ('A1', 41.5, 12.5, 'Lazio'),  # A1 Milano-Napoli
    'dt2': ('A4', 45.4, 12.3, 'Veneto'),  # A4 Torino-Trieste
    'dt3': ('A7', 44.6, 8.7, 'Piemonte'),  # A7 Genova-Serravalle
    'dt4': ('A14', 44.5, 11.3, 'Emilia-Romagna'),  # A14 Bologna-Taranto
    'dt5': ('A22', 45.4, 10.9, 'Lombardia'),  # A22 Brennero-Modena
    'dt6': ('A10', 44.4, 8.9, 'Liguria'),  # A10 Genova-Ventimiglia
    'dt7': ('A26', 45.3, 8.6, 'Piemonte'),  # A26 Genova-Gravellona
    'dt8': ('A8', 45.5, 8.8, 'Lombardia'),  # A8 Milano-Varese
    'dt9': ('A9', 45.6, 9.0, 'Lombardia'),  # A9 Lainate-Como
}


def normalize_country_code(name):
    """Map 2-letter ISO code to full country name."""
    if not name:
        return name
    name = name.strip()
    if name in ISO2_TO_NAME:
        return ISO2_TO_NAME[name]
    return name


def main():
    # Load TV catalog to get more accurate autostrade coords
    print("Loading TV catalog for autostrade coords...", flush=True)
    t0 = time.time()
    with open(TV_CATALOG, 'r', encoding='utf-8') as f:
        tv = json.load(f)
    tv_auto = [c for c in tv.get('cameras', []) if c.get('source') == 'autostrade']
    print(f"  Loaded {len(tv_auto)} autostrade TV cams in {time.time()-t0:.1f}s", flush=True)

    # Build per-highway TV coords (use avg of TV cams per highway)
    # TV has no highway tag, so just use overall median of TV coords for autostrade
    auto_lats = [c.get('lat') for c in tv_auto if c.get('lat') is not None]
    auto_lngs = [c.get('lng') for c in tv_auto if c.get('lng') is not None]
    if auto_lats:
        median_lat = sorted(auto_lats)[len(auto_lats) // 2]
        median_lng = sorted(auto_lngs)[len(auto_lngs) // 2]
        print(f"  Median autostrade TV coords: {median_lat}, {median_lng}", flush=True)
    else:
        median_lat, median_lng = 41.9, 12.5

    # Read CSV
    print("Reading CSV...", flush=True)
    t0 = time.time()
    with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    print(f"  Read {len(rows)} rows in {time.time()-t0:.1f}s", flush=True)

    IDX = {col: i for i, col in enumerate(header)}
    COL_URL = IDX['url']
    COL_LIVE = IDX['live_stream_url']
    COL_COUNTRY = IDX['country']
    COL_REGION = IDX['region']
    COL_CITY = IDX['city']
    COL_LAT = IDX['lat']
    COL_LON = IDX['lon']
    COL_GEO_SRC = IDX['geo_source']

    stats = Counter()

    print("Processing cleanup...", flush=True)
    t0 = time.time()
    for i, row in enumerate(rows):
        if i % 30000 == 0 and i > 0:
            elapsed = time.time() - t0
            rate = i / elapsed
            print(f"  {i}/{len(rows)} ({rate:.0f}/s) {dict(stats)}", flush=True)

        old_country = row[COL_COUNTRY] if COL_COUNTRY < len(row) else ''
        old_region = row[COL_REGION] if COL_REGION < len(row) else ''
        old_lat = row[COL_LAT] if COL_LAT < len(row) else ''
        old_lon = row[COL_LON] if COL_LON < len(row) else ''

        # 1. ISO2 to full name
        new_country = normalize_country_code(old_country)
        if new_country != old_country:
            row[COL_COUNTRY] = new_country
            stats['iso2_to_name'] += 1

        # 2. Autostrade highway distribution
        url = ''
        if COL_URL < len(row):
            url += row[COL_URL] + ' '
        if COL_LIVE < len(row):
            url += row[COL_LIVE]
        if 'autostrade' in url:
            m = re.search(r'/dt(\d+)/', url)
            if m:
                dt = f'dt{m.group(1)}'
                if dt in AUTOSTRADE_HIGHWAYS:
                    name, lat, lon, region = AUTOSTRADE_HIGHWAYS[dt]
                    if not old_lat or not old_lon or (old_lat and float(old_lat) == 45.22638 and float(old_lon) == 8.47637):
                        # Use highway center
                        # Add small jitter so they're not all on top
                        import hashlib
                        h = int(hashlib.md5(row[0].encode()).hexdigest()[:8], 16)
                        jitter_lat = (h % 200 - 100) / 100.0 * 0.3
                        jitter_lon = ((h // 200) % 200 - 100) / 100.0 * 0.3
                        row[COL_LAT] = str(round(lat + jitter_lat, 5))
                        row[COL_LON] = str(round(lon + jitter_lon, 5))
                        row[COL_COUNTRY] = 'Italy'
                        row[COL_REGION] = region
                        stats['autostrade_dt'] += 1

    print(f"\nProcessed {len(rows)} in {time.time()-t0:.1f}s", flush=True)
    print(f"Stats: {dict(stats)}", flush=True)

    # Final country distribution
    print("\nFinal country distribution:", flush=True)
    countries = Counter()
    for row in rows:
        c = row[COL_COUNTRY] if COL_COUNTRY < len(row) else ''
        countries[c] += 1
    for c, n in countries.most_common(30):
        print(f"  {n:>8}  {c}")

    print("\nWriting atomic CSV...", flush=True)
    tmp = CSV_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        w.writerow(header)
        for row in rows:
            w.writerow(row)
    os.replace(tmp, CSV_PATH)
    print(f"Done. Saved to {CSV_PATH}", flush=True)


if __name__ == '__main__':
    main()
