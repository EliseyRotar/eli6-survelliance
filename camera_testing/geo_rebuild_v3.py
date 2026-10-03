"""
geo_rebuild_v3.py - Second pass: clean up country names + region/city
- Normalize country names (Italia -> Italy, Brasil -> Brazil, etc.)
- For rows that got country but kept bogus region/city, wipe region/city if they don't match
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
PROGRESS_PATH = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\geo_rebuild_v3_progress.json"

# Map of common country name variants to canonical English
COUNTRY_CANON = {
    'United States': 'United States', 'United States of America': 'United States',
    'USA': 'United States', 'US': 'United States', 'U.S.A.': 'United States',
    'United Kingdom': 'United Kingdom', 'UK': 'United Kingdom', 'Britain': 'United Kingdom',
    'Great Britain': 'United Kingdom', 'England': 'United Kingdom', 'Scotland': 'United Kingdom',
    'Wales': 'United Kingdom', 'Northern Ireland': 'United Kingdom',
    'Italia (Italy)': 'Italy', 'Italy': 'Italy', 'Italia': 'Italy',
    'Brasil (Brazil)': 'Brazil', 'Brazil': 'Brazil', 'Brasil': 'Brazil',
    'España (Spain)': 'Spain', 'Spain': 'Spain', 'España': 'Spain',
    'Deutschland (Germany)': 'Germany', 'Germany': 'Germany', 'Deutschland': 'Germany',
    'France': 'France', '日本 (Japan)': 'Japan', 'Japan': 'Japan', '日本': 'Japan',
    '中国 (China)': 'China', 'China': 'China', '中国': 'China',
    '臺灣 (Taiwan)': 'Taiwan', 'Taiwan': 'Taiwan', '臺灣': 'Taiwan', '台湾': 'Taiwan',
    'Korea': 'South Korea', 'South Korea': 'South Korea', 'Republic of Korea': 'South Korea',
    '대한민국 (Republic of Korea)': 'South Korea',
    'North Korea': 'North Korea', '日本 (Japan)': 'Japan',
    'Россия (Russia)': 'Russia', 'Russia': 'Russia', 'Россия': 'Russia',
    'Беларусь (Belarus)': 'Belarus', 'Belarus': 'Belarus', 'Беларусь': 'Belarus',
    'Україна (Ukraine)': 'Ukraine', 'Ukraine': 'Ukraine', 'Україна': 'Ukraine',
    'ไทย (Thailand)': 'Thailand', 'Thailand': 'Thailand', 'ประเทศไทย': 'Thailand',
    'Éire (Ireland)': 'Ireland', 'Ireland': 'Ireland', 'Éire': 'Ireland', 'Eire': 'Ireland',
    'Magyarország (Hungary)': 'Hungary', 'Hungary': 'Hungary', 'Magyarország': 'Hungary',
    'Česko (Czechia)': 'Czech Republic', 'Czechia': 'Czech Republic', 'Czech Republic': 'Czech Republic',
    'Slovensko (Slovakia)': 'Slovakia', 'Slovakia': 'Slovakia', 'Slovensko': 'Slovakia',
    'Hrvatska (Croatia)': 'Croatia', 'Croatia': 'Croatia', 'Hrvatska': 'Croatia',
    'Србија (Serbia)': 'Serbia', 'Serbia': 'Serbia', 'Србија': 'Serbia',
    'România (Romania)': 'Romania', 'Romania': 'Romania', 'România': 'Romania',
    'Ελλάς (Greece)': 'Greece', 'Greece': 'Greece', 'Ελλάς': 'Greece', 'Ελλάδα': 'Greece',
    'ישראל (Israel)': 'Israel', 'Israel': 'Israel', 'ישראל': 'Israel',
    'Türkiye (Turkey)': 'Turkey', 'Turkey': 'Turkey', 'Türkiye': 'Turkey', 'T?rkiye': 'Turkey',
    'Suomi (Finland)': 'Finland', 'Finland': 'Finland', 'Suomi': 'Finland',
    'Norge (Norway)': 'Norway', 'Norway': 'Norway', 'Norge': 'Norway',
    'Sverige (Sweden)': 'Sweden', 'Sweden': 'Sweden', 'Sverige': 'Sweden',
    'Danmark (Denmark)': 'Denmark', 'Denmark': 'Denmark', 'Danmark': 'Denmark',
    'Nederland (Netherlands)': 'Netherlands', 'Netherlands': 'Netherlands', 'Nederland': 'Netherlands',
    'België (Belgium)': 'Belgium', 'Belgium': 'Belgium', 'België': 'Belgium',
    'Schweiz (Switzerland)': 'Switzerland', 'Switzerland': 'Switzerland', 'Schweiz': 'Switzerland',
    'Österreich (Austria)': 'Austria', 'Austria': 'Austria', 'Österreich': 'Austria',
    'Polska (Poland)': 'Poland', 'Poland': 'Poland', 'Polska': 'Poland',
    'México (Mexico)': 'Mexico', 'Mexico': 'Mexico', 'México': 'Mexico',
    'Perú (Peru)': 'Peru', 'Peru': 'Peru', 'Perú': 'Peru',
    'Việt Nam (Vietnam)': 'Vietnam', 'Vietnam': 'Vietnam', 'Việt Nam': 'Vietnam',
    'ประเทศไทย (Thailand)': 'Thailand',
    'Aotearoa (New Zealand)': 'New Zealand', 'New Zealand': 'New Zealand', 'Aotearoa': 'New Zealand',
    'Российская Федерация': 'Russia',
    'Кыргызстан (Kyrgyzstan)': 'Kyrgyzstan',
    'Қазақстан (Kazakhstan)': 'Kazakhstan',
    'Србија (Serbia)': 'Serbia',
    'Северна Македонија (North Macedonia)': 'North Macedonia',
    'Република Србија': 'Serbia',
    'العراق (Iraq)': 'Iraq',
    'ایران (Iran)': 'Iran',
    'الأردن (Jordan)': 'Jordan',
    'الإمارات العربية المتحدة (United Arab Emirates)': 'United Arab Emirates',
    'السعودية (Saudi Arabia)': 'Saudi Arabia',
    'مصر (Egypt)': 'Egypt',
    'فلسطين (Palestine)': 'Palestine',
    'မြန်မာ (Myanmar)': 'Myanmar',
    'საქართველო (Georgia)': 'Georgia',
    'Slovenija (Slovenia)': 'Slovenia', 'Slovenia': 'Slovenia', 'Slovenija': 'Slovenia',
    'Lietuva (Lithuania)': 'Lithuania', 'Lithuania': 'Lithuania', 'Lietuva': 'Lithuania',
    'Latvija (Latvia)': 'Latvia', 'Latvia': 'Latvia', 'Latvija': 'Latvia',
    'Eesti (Estonia)': 'Estonia', 'Estonia': 'Estonia', 'Eesti': 'Estonia',
    'Lëtzebuerg (Luxembourg)': 'Luxembourg', 'Luxembourg': 'Luxembourg', 'Lëtzebuerg': 'Luxembourg',
    'Maroc (Morocco)': 'Morocco', 'Morocco': 'Morocco', 'Maroc': 'Morocco',
    'Bosna i Hercegovina (Bosnia and Herzegovina)': 'Bosnia and Herzegovina',
    'Crna Gora (Montenegro)': 'Montenegro', 'Montenegro': 'Montenegro', 'Crna Gora': 'Montenegro',
    'Hayastan (Armenia)': 'Armenia', 'Armenia': 'Armenia', 'Hayastan': 'Armenia',
    'Dhivehi Raajje (Maldives)': 'Maldives', 'Maldives': 'Maldives', 'Dhivehi Raajje': 'Maldives',
    'Città del Vaticano (Vatican City)': 'Vatican City', 'Vatican City': 'Vatican City',
    'Falkland Islands': 'Falkland Islands',
    'Cabo Verde (Cape Verde)': 'Cape Verde', 'Cape Verde': 'Cape Verde', 'Cabo Verde': 'Cape Verde',
    'Moçambique (Mozambique)': 'Mozambique', 'Mozambique': 'Mozambique', 'Moçambique': 'Mozambique',
    'Kalaallit Nunaat (Greenland)': 'Greenland', 'Greenland': 'Greenland', 'Kalaallit Nunaat': 'Greenland',
    'Panamá (Panama)': 'Panama', 'Panama': 'Panama', 'Panamá': 'Panama',
    'Papua Niugini': 'Papua New Guinea', 'Papua New Guinea': 'Papua New Guinea',
    'Sénégal (Senegal)': 'Senegal', 'Senegal': 'Senegal', 'Sénégal': 'Senegal',
    'The Netherlands': 'Netherlands',
    'The Bahamas': 'Bahamas', 'Bahamas': 'Bahamas', 'The Bahamas': 'Bahamas',
    'République démocratique du Congo (Democratic Republic of Congo)': 'Democratic Republic of the Congo',
    'Bermuda': 'Bermuda',
    'Føroyar (Faroe Islands)': 'Faroe Islands', 'Faroe Islands': 'Faroe Islands', 'Føroyar': 'Faroe Islands',
    'Polska (Poland)': 'Poland',
}

# Country -> known regions list (canonical English names)
# Used to validate that a row's region actually belongs to the country
COUNTRY_STATES = {
    'United States': {  # US states + territories
        'Alabama','Alaska','Arizona','Arkansas','California','Colorado','Connecticut',
        'Delaware','Florida','Georgia','Hawaii','Idaho','Illinois','Indiana','Iowa',
        'Kansas','Kentucky','Louisiana','Maine','Maryland','Massachusetts','Michigan',
        'Minnesota','Mississippi','Missouri','Montana','Nebraska','Nevada',
        'New Hampshire','New Jersey','New Mexico','New York','North Carolina',
        'North Dakota','Ohio','Oklahoma','Oregon','Pennsylvania','Rhode Island',
        'South Carolina','South Dakota','Tennessee','Texas','Utah','Vermont',
        'Virginia','Washington','West Virginia','Wisconsin','Wyoming',
        'District of Columbia','Puerto Rico','Guam','US Virgin Islands',
        'American Samoa','Northern Mariana Islands',
        # Abbreviations
        'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN',
        'IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV',
        'NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN',
        'TX','UT','VT','VA','WA','WV','WI','WY','DC','PR',
    },
    'Canada': {
        'Ontario','Quebec','British Columbia','Alberta','Manitoba','Saskatchewan',
        'Nova Scotia','New Brunswick','Newfoundland and Labrador','Prince Edward Island',
        'Yukon','Northwest Territories','Nunavut',
        'ON','QC','BC','AB','MB','SK','NS','NB','NL','PE','YT','NT','NU',
    },
    'Mexico': {
        'Aguascalientes','Baja California','Baja California Sur','Campeche','Chiapas',
        'Chihuahua','Coahuila','Colima','Durango','Guanajuato','Guerrero','Hidalgo',
        'Jalisco','Mexico City','México','Michoacán','Morelos','Nayarit','Nuevo León',
        'Oaxaca','Puebla','Querétaro','Quintana Roo','San Luis Potosí','Sinaloa',
        'Sonora','Tabasco','Tamaulipas','Tlaxcala','Veracruz','Yucatán','Zacatecas',
    },
    'Australia': {
        'New South Wales','Victoria','Queensland','Western Australia','South Australia',
        'Tasmania','Australian Capital Territory','Northern Territory',
        'NSW','VIC','QLD','WA','SA','TAS','ACT','NT',
    },
    'Italy': {
        'Piemonte','Lombardia','Veneto','Trentino-Alto Adige','Friuli Venezia Giulia',
        'Liguria','Emilia-Romagna','Toscana','Umbria','Marche','Lazio','Abruzzo',
        'Molise','Campania','Puglia','Basilicata','Calabria','Sicilia','Sardegna',
        'Valle d\'Aosta','Aosta',
    },
    'Germany': {
        'Baden-Wuerttemberg','Bavaria','Berlin','Brandenburg','Bremen','Hamburg',
        'Hesse','Lower Saxony','Mecklenburg-Vorpommern','North Rhine-Westphalia',
        'Rhineland-Palatinate','Saarland','Saxony','Saxony-Anhalt','Schleswig-Holstein','Thuringia',
    },
    'Japan': {
        'Hokkaido','Aomori','Iwate','Miyagi','Akita','Yamagata','Fukushima',
        'Ibaraki','Tochigi','Gunma','Saitama','Chiba','Tokyo','Kanagawa',
        'Niigata','Toyama','Ishikawa','Fukui','Yamanashi','Nagano','Gifu',
        'Shizuoka','Aichi','Mie','Shiga','Kyoto','Osaka','Hyogo','Nara',
        'Wakayama','Tottori','Shimane','Okayama','Hiroshima','Yamaguchi',
        'Tokushima','Kagawa','Ehime','Kochi','Fukuoka','Saga','Nagasaki',
        'Kumamoto','Oita','Miyazaki','Kagoshima','Okinawa',
    },
}


def canonical_country(name):
    if not name:
        return ''
    name = name.strip()
    if name in COUNTRY_CANON:
        return COUNTRY_CANON[name]
    return name  # return as-is if unknown


def is_valid_region(country, region):
    """Check if region plausibly belongs to country."""
    if not region:
        return True  # empty is fine
    if country not in COUNTRY_STATES:
        return True  # unknown country, accept all
    states = COUNTRY_STATES[country]
    if region in states:
        return True
    # Try case-insensitive
    if region.lower() in {s.lower() for s in states}:
        return True
    return False


def main():
    print("Reading CSV...", flush=True)
    t0 = time.time()
    with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    print(f"  Read {len(rows)} rows in {time.time()-t0:.1f}s", flush=True)

    IDX = {col: i for i, col in enumerate(header)}
    COL_COUNTRY = IDX['country']
    COL_REGION = IDX['region']
    COL_CITY = IDX['city']

    stats = Counter()
    samples = []
    country_changes = Counter()
    region_wipes = Counter()

    print("Normalizing countries + cleaning regions...", flush=True)
    t0 = time.time()
    for i, row in enumerate(rows):
        if i % 20000 == 0 and i > 0:
            elapsed = time.time() - t0
            rate = i / elapsed
            print(f"  {i}/{len(rows)} ({rate:.0f}/s) {dict(stats)}", flush=True)
            with open(PROGRESS_PATH, 'w') as pf:
                json.dump({'stats': dict(stats), 'last_idx': i}, pf)

        old_country = row[COL_COUNTRY] if COL_COUNTRY < len(row) else ''
        old_region = row[COL_REGION] if COL_REGION < len(row) else ''
        old_city = row[COL_CITY] if COL_CITY < len(row) else ''

        new_country = canonical_country(old_country)
        if new_country != old_country:
            row[COL_COUNTRY] = new_country
            stats['country_normalized'] += 1
            country_changes[(old_country, new_country)] += 1

        # Validate region against country
        if new_country and old_region and not is_valid_region(new_country, old_region):
            row[COL_REGION] = ''
            row[COL_CITY] = ''  # also wipe city (likely from same bad source)
            stats['region_wiped'] += 1
            region_wipes[(new_country, old_region)] += 1
            if len(samples) < 20:
                samples.append(f'Wiped region/city for {new_country}: was {old_region}/{old_city}')

    print(f"\nProcessed {len(rows)} in {time.time()-t0:.1f}s", flush=True)
    print(f"Stats: {dict(stats)}", flush=True)

    print(f"\nTop country normalizations:")
    for (old, new), c in country_changes.most_common(30):
        print(f"  {c:>6}  {old!r} -> {new!r}")

    print(f"\nTop region wipes (country/old_region):")
    for (co, reg), c in region_wipes.most_common(20):
        print(f"  {c:>6}  {co!r} / {reg!r}")

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
