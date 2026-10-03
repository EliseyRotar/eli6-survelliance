"""Normalize country names in CSV.

The CSV has 'US' and 'United States' both. Normalize to full names consistently.
Also handle other variants like 'UK'/'United Kingdom', 'PR'/'Puerto Rico', etc.

ISO 3166-1 alpha-2 to canonical English name.
"""
import csv
import os
import re

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'

# 2-letter codes mapped to full names
ISO2_TO_NAME = {
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
    "AL": "Albania", "MK": "North Macedonia", "ME": "Montenegro",
    "PR": "Puerto Rico", "GL": "Greenland",
    "BM": "Bermuda", "VI": "U.S. Virgin Islands", "GU": "Guam",
    "MP": "Northern Mariana Islands", "AS": "American Samoa",
    "KY": "Cayman Islands", "TC": "Turks and Caicos Islands",
    "AW": "Aruba", "CW": "Curaçao",
}

# Reverse: any non-canonical names -> canonical
# Add known variants
VARIANTS = {
    "USA": "United States",
    "U.S.": "United States",
    "U.S.A.": "United States",
    "UK": "United Kingdom",
    "U.K.": "United Kingdom",
    "Britain": "United Kingdom",
    "Great Britain": "United Kingdom",
    "Korea": "South Korea",
    "South Korea": "South Korea",
    "Republic of Korea": "South Korea",
    "Czechia": "Czech Republic",
    "Russia": "Russia",
    "Russian Federation": "Russia",
    "Iran": "Iran",
    "Iran, Islamic Republic of": "Iran",
    "Syria": "Syria",
    "Syrian Arab Republic": "Syria",
    "Vietnam": "Vietnam",
    "Viet Nam": "Vietnam",
    "Laos": "Laos",
    "Tanzania": "Tanzania",
    "Tanzania, United Republic of": "Tanzania",
    "Macedonia": "North Macedonia",
    "Republic of North Macedonia": "North Macedonia",
    "Burma": "Myanmar",
}


def normalize(country):
    if not country:
        return ''
    country = country.strip()
    # 2-letter ISO code
    if len(country) == 2 and country.upper() in ISO2_TO_NAME:
        return ISO2_TO_NAME[country.upper()]
    # Variants
    if country in VARIANTS:
        return VARIANTS[country]
    if country.upper() in VARIANTS:
        return VARIANTS[country.upper()]
    # Already in canonical form (assumed)
    return country


def main():
    with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    header = rows[0]
    cols = {h: i for i, h in enumerate(header)}
    if 'country' not in cols:
        print('no country col')
        return
    CCY = cols['country']

    updated = 0
    for r in rows[1:]:
        if len(r) <= CCY:
            continue
        orig = r[CCY]
        new = normalize(orig)
        if new != orig:
            r[CCY] = new
            updated += 1
    print(f'normalized {updated} country entries')

    tmp = CSV_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
        for r in rows:
            w.writerow(r)
    os.replace(tmp, CSV_PATH)
    print(f'done. CSV written.')

    # Recount
    from collections import Counter
    ctr = Counter()
    for r in rows[1:]:
        if len(r) > CCY and r[CCY]:
            ctr[r[CCY]] += 1
    print(f'top 10:')
    for c, n in sorted(ctr.items(), key=lambda x: -x[1])[:10]:
        print(f'  {c}: {n}')


if __name__ == '__main__':
    main()
