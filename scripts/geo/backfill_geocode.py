"""Backfill country + city for cameras that have lat/lon but empty country/city.

Uses offline reverse_geocoder (GeoNames cities1000 baked in).
- 11 seconds for 60k lookups
- No API key, no rate limit
- Caches results by (lat, lon) rounded to 4 decimal places (~11m precision)

CSV is updated in place (atomic write via .tmp + os.replace).
"""
import csv
import os
import pickle
import sys
import time

import reverse_geocoder as rg

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'
CACHE_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\backups\geocode_cache.pkl'

# ISO 3166-1 alpha-2 to full country name
ISO_TO_NAME = {
    "US": "United States", "GB": "United Kingdom", "KR": "South Korea",
    "JP": "Japan", "DE": "Germany", "FR": "France", "IT": "Italy",
    "CA": "Canada", "AU": "Australia", "BR": "Brazil", "IN": "India",
    "MX": "Mexico", "RU": "Russia", "CN": "China", "ES": "Spain",
    "NL": "Netherlands", "SE": "Sweden", "NO": "Norway", "FI": "Finland",
    "DK": "Denmark", "PL": "Poland", "CH": "Switzerland", "AT": "Austria",
    "BE": "Belgium", "IE": "Ireland", "PT": "Portugal", "GR": "Greece",
    "TR": "Turkey", "ID": "Indonesia", "TH": "Thailand", "VN": "Vietnam",
    "PH": "Philippines", "MY": "Malaysia", "SG": "Singapore", "HK": "Hong Kong",
    "TW": "Taiwan", "NZ": "New Zealand", "ZA": "South Africa", "EG": "Egypt",
    "AR": "Argentina", "CL": "Chile", "CO": "Colombia", "PE": "Peru",
    "VE": "Venezuela", "IL": "Israel", "AE": "United Arab Emirates",
    "SA": "Saudi Arabia", "CZ": "Czech Republic", "SK": "Slovakia",
    "HU": "Hungary", "RO": "Romania", "BG": "Bulgaria", "UA": "Ukraine",
    "HR": "Croatia", "RS": "Serbia", "SI": "Slovenia", "BA": "Bosnia and Herzegovina",
    "AL": "Albania", "MK": "North Macedonia", "ME": "Montenegro", "LT": "Lithuania",
    "LV": "Latvia", "EE": "Estonia", "IS": "Iceland", "LU": "Luxembourg",
    "MT": "Malta", "CY": "Cyprus", "MA": "Morocco", "TN": "Tunisia",
    "DZ": "Algeria", "LY": "Libya", "ET": "Ethiopia", "KE": "Kenya",
    "GH": "Ghana", "NG": "Nigeria", "TZ": "Tanzania", "UG": "Uganda",
    "ZW": "Zimbabwe", "BW": "Botswana", "NA": "Namibia", "MZ": "Mozambique",
    "AO": "Angola", "ZM": "Zambia", "MW": "Malawi", "MG": "Madagascar",
    "MU": "Mauritius", "SN": "Senegal", "CI": "Côte d'Ivoire", "CM": "Cameroon",
    "CD": "DR Congo", "CG": "Congo", "GA": "Gabon", "BJ": "Benin",
    "TG": "Togo", "BF": "Burkina Faso", "ML": "Mali", "NE": "Niger",
    "TD": "Chad", "SD": "Sudan", "ER": "Eritrea", "SO": "Somalia",
    "DJ": "Djibouti", "YE": "Yemen", "OM": "Oman", "QA": "Qatar",
    "BH": "Bahrain", "KW": "Kuwait", "JO": "Jordan", "LB": "Lebanon",
    "SY": "Syria", "IQ": "Iraq", "IR": "Iran", "AF": "Afghanistan",
    "PK": "Pakistan", "BD": "Bangladesh", "NP": "Nepal", "BT": "Bhutan",
    "LK": "Sri Lanka", "MM": "Myanmar", "KH": "Cambodia", "LA": "Laos",
    "MN": "Mongolia", "KP": "North Korea", "BN": "Brunei", "TL": "Timor-Leste",
    "PG": "Papua New Guinea", "FJ": "Fiji", "NC": "New Caledonia", "VU": "Vanuatu",
    "SB": "Solomon Islands", "TO": "Tonga", "WS": "Samoa", "KI": "Kiribati",
    "TV": "Tuvalu", "NR": "Nauru", "PW": "Palau", "FM": "Micronesia",
    "MH": "Marshall Islands", "PY": "Paraguay", "UY": "Uruguay", "BO": "Bolivia",
    "GY": "Guyana", "SR": "Suriname", "GF": "French Guiana", "FK": "Falkland Islands",
    "PA": "Panama", "CR": "Costa Rica", "NI": "Nicaragua", "HN": "Honduras",
    "SV": "El Salvador", "GT": "Guatemala", "BZ": "Belize", "CU": "Cuba",
    "JM": "Jamaica", "HT": "Haiti", "DO": "Dominican Republic", "BS": "Bahamas",
    "BB": "Barbados", "TT": "Trinidad and Tobago", "GD": "Grenada", "LC": "Saint Lucia",
    "VC": "Saint Vincent and the Grenadines", "AG": "Antigua and Barbuda",
    "DM": "Dominica", "KN": "Saint Kitts and Nevis", "AW": "Aruba",
    "CW": "Curaçao", "SX": "Sint Maarten", "TC": "Turks and Caicos",
    "KY": "Cayman Islands", "BM": "Bermuda", "PR": "Puerto Rico",
    "VI": "U.S. Virgin Islands", "GU": "Guam", "MP": "Northern Mariana Islands",
    "AS": "American Samoa", "AQ": "Antarctica", "BV": "Bouvet Island",
    "HM": "Heard Island", "TF": "French Southern Territories",
    "IO": "British Indian Ocean Territory", "CX": "Christmas Island",
    "CC": "Cocos Islands", "NF": "Norfolk Island", "PN": "Pitcairn",
    "SH": "Saint Helena", "PM": "Saint Pierre and Miquelon", "FO": "Faroe Islands",
    "GL": "Greenland", "SJ": "Svalbard and Jan Mayen", "AX": "Åland Islands",
    "GI": "Gibraltar", "JE": "Jersey", "GG": "Guernsey", "IM": "Isle of Man",
    "LI": "Liechtenstein", "MC": "Monaco", "SM": "San Marino", "VA": "Vatican City",
    "AD": "Andorra", "MD": "Moldova", "BY": "Belarus", "AM": "Armenia",
    "AZ": "Azerbaijan", "GE": "Georgia", "KZ": "Kazakhstan", "UZ": "Uzbekistan",
    "TM": "Turkmenistan", "KG": "Kyrgyzstan", "TJ": "Tajikistan",
    "RE": "Réunion", "YT": "Mayotte", "GP": "Guadeloupe", "MQ": "Martinique",
    "PM": "Saint Pierre and Miquelon",
}


def load_cache():
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, 'rb') as f:
                return pickle.load(f)
        except Exception:
            return {}
    return {}


def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, 'wb') as f:
        pickle.dump(cache, f, protocol=pickle.HIGHEST_PROTOCOL)


def round_key(lat, lon, decimals=4):
    return (round(float(lat), decimals), round(float(lon), decimals))


def main():
    print(f'[init] reading {CSV_PATH}')
    with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    header = rows[0]
    print(f'[init] {len(rows)-1} rows, header has {len(header)} columns')

    # Column indexes
    cols = {h: i for i, h in enumerate(header)}
    required = ['lat', 'lon', 'country', 'city', 'region']
    for r in required:
        if r not in cols:
            print(f'[ERR] missing column {r}')
            return

    LAT = cols['lat']
    LON = cols['lon']
    CCY = cols['country']
    CREG = cols['region']
    CCI = cols['city']

    cache = load_cache()
    print(f'[cache] loaded {len(cache)} cached entries')

    # Find rows that need backfill (have lat/lon but missing country OR city)
    needs_geo = []
    skipped = 0
    for i, r in enumerate(rows[1:], start=1):
        if len(r) <= max(LAT, LON, CCY, CCI, CREG):
            skipped += 1
            continue
        if not r[LAT].strip() or not r[LON].strip():
            continue
        try:
            lat = float(r[LAT]); lon = float(r[LON])
        except ValueError:
            continue
        # Skip if both country and city already filled
        if r[CCY].strip() and r[CCI].strip():
            continue
        needs_geo.append(i)
    print(f'[plan] needs_geo: {len(needs_geo)}, skipped: {skipped}')

    if not needs_geo:
        print('[done] no rows need backfill')
        return

    # Build unique point set
    unique_pts = set()
    for i in needs_geo:
        lat = float(rows[i][LAT]); lon = float(rows[i][LON])
        unique_pts.add(round_key(lat, lon))
    to_lookup = unique_pts - set(cache.keys())
    print(f'[plan] unique points: {len(unique_pts)}, new lookups: {len(to_lookup)}')

    # Bulk lookup
    if to_lookup:
        print(f'[lookup] running reverse_geocoder on {len(to_lookup)} points...')
        t0 = time.time()
        coords = list(to_lookup)
        # rg.search accepts list of (lat, lon) tuples; process in chunks of 10k for memory
        results = []
        chunk = 10000
        for i in range(0, len(coords), chunk):
            print(f'  chunk {i}-{min(i+chunk, len(coords))}...')
            results.extend(rg.search(coords[i:i+chunk]))
        for (lat, lon), res in zip(coords, results):
            cc = res['cc']
            country_name = ISO_TO_NAME.get(cc, cc)
            city = res.get('name', '')
            admin1 = res.get('admin1', '')
            cache[(lat, lon)] = {
                'country_iso': cc,
                'country': country_name,
                'city': city,
                'region': admin1,
            }
        save_cache(cache)
        print(f'[lookup] done in {time.time()-t0:.1f}s')

    # Apply to rows
    updated_country = 0
    updated_city = 0
    updated_region = 0
    for i in needs_geo:
        try:
            lat = float(rows[i][LAT]); lon = float(rows[i][LON])
        except ValueError:
            continue
        k = round_key(lat, lon)
        if k not in cache:
            continue
        info = cache[k]
        if not rows[i][CCY].strip() and info['country']:
            rows[i][CCY] = info['country']
            updated_country += 1
        if not rows[i][CCI].strip() and info['city']:
            rows[i][CCI] = info['city']
            updated_city += 1
        if not rows[i][CREG].strip() and info['region']:
            rows[i][CREG] = info['region']
            updated_region += 1

    print(f'[apply] updated country={updated_country}, city={updated_city}, region={updated_region}')

    # Write back atomically
    tmp = CSV_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
        for r in rows:
            w.writerow(r)
    os.replace(tmp, CSV_PATH)
    print(f'[done] CSV written to {CSV_PATH}')


if __name__ == '__main__':
    main()
