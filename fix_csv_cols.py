"""fix_csv_cols.py — Fix rows where lat/lon/org fell into wrong columns due to width mismatch.

Detect rows with shifted data:
- Col 23 (address) contains a number that looks like a lat (e.g. '49.839')
- Col 24 (lat) contains a number that looks like a lon
- Col 25 (lon) contains text that's actually org/asn

Shift them back: col 23 = lat, col 24 = lon, col 25+ shift right
"""
import csv
import os
import re

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'

with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
    rows = list(csv.reader(f))
header = rows[0]

# Detect shift: col 23 should be address (text), col 24 should be lat (number), col 25 should be lon (number)
# If col 23 looks like a lat (number) AND col 24 also number, AND col 25 looks like text (org/isp), shift is present
fixed = 0
new_rows = [header]
for r in rows[1:]:
    if len(r) < len(header):
        # Pad to header length
        r = r + [''] * (len(header) - len(r))
    elif len(r) > len(header):
        # Truncate
        r = r[:len(header)]

    # Check col 23 (address) — should be text or empty
    addr = r[23] if len(r) > 23 else ''
    lat = r[24] if len(r) > 24 else ''
    lon = r[25] if len(r) > 25 else ''

    # Detect shift: col 23 = number, col 24 = number, col 25 = text containing 'AS' or non-numeric
    is_shift = False
    if re.match(r'^-?\d+\.?\d*$', addr.strip()) and re.match(r'^-?\d+\.?\d*$', lat.strip()):
        # Both col 23 and col 24 are numeric
        if lon and not re.match(r'^-?\d+\.?\d*$', lon.strip()):
            # col 25 is non-numeric (text like 'NVTOV "SOLVER"')
            is_shift = True

    if is_shift:
        # Shift back: col 23 should be col 24 (real lat), col 24 should be col 25 (real lon)
        # But col 25 was originally some text — we need to shift the text forward
        # Actually the issue: col 23=real_lat, col 24=real_lon, col 25=text, col 26+ shifted
        # To fix: move col 23 to col 24 (lat), col 24 to col 25 (lon), col 25 to col 23 (address)
        # Wait, that loses the actual address. Better: shift everything forward by 2:
        # col 23 was lat, col 24 was lon, col 25 was geo_source, col 26+ shifted
        # We have correct data in cols 23-24 (lat/lon) but col 25 (should be lon) has geo_source content
        # Let's just move things to right positions:
        # addr(23) <- "shifted-from-col25"
        # lat(24) <- col23 (real lat)
        # lon(25) <- col24 (real lon)
        # But then col 25 (which should be lon) gets col24, and col26 onward shift correctly
        # Actually for this case we need to MOVE col25..col33 into col23..col31, then col24,25 get real lat/lon

        # Build new row
        new_r = list(r)  # copy
        # Move col 25 onward to col 23 onward (shift left by 2)
        for j in range(23, 33 - 2):
            new_r[j] = r[j + 2]
        # Fill col 23, 24 with the real lat/lon from original cols 23, 24
        # Wait — original col 23 is the "shifted" lat, col 24 is shifted lon
        # Original col 25 had text (org name), original col 26 was isp (text)
        # After shift: new_r[23] = original r[25] (text), new_r[24] = original r[26] (text)
        # That doesn't recover the lat/lon...

        # Better approach: figure out the mapping
        # Real column meanings in a clean row: idx, project_name, url, lsu, type, auth_required,
        #   auth_user, auth_pass, enabled, live_status, http_status, content_type, server_header,
        #   page_title, description, category, likely_subject, brand, model, country, region, city,
        #   zip, address, lat, lon, geo_source, isp, org, asn, reverse_dns, host, confidence, notes, csv_id

        # In the broken row: cols 0-22 are correct. col 23-33 are shifted by 2.
        # Original 23 should be address (text), but contains 49.839 (real lat)
        # Original 24 should be lat, but contains 24.0191 (real lon)
        # Original 25 should be lon, but contains NVTOV "SOLVER" (real org)
        # Original 26 should be geo_source, but contains "Science Production..." (real ?)
        # Original 27 should be isp, but contains "AS15461 NVTOV..." (real ASN)
        # Original 28 should be org, but contains 194.44.38.196 (real host)
        # Original 29 should be asn, but contains medium (real confidence)
        # Original 30 should be reverse_dns, but contains disc_63943 (real csv_id?)
        # Original 31 should be host, but contains Family=... (real notes)
        # Original 32 should be confidence (missing)

        # So shift left by 2: col 23 gets real 25 (org), col 24 gets real 26 (asn),
        # col 25 gets real 27 (reverse_dns? no, asn), etc.
        # Actually we lose the lat/lon/original info.

        # NEW APPROACH: For broken rows, just shift everything by 2 cols left starting at 23
        # This means we lose 2 cols of data (address and geo_source) but recover lat/lon/org/etc.
        # We can rebuild address as empty and geo_source as 'tier4:ipapi-shifted-fix'

        new_r = list(r[:23])  # idx through zip (cols 0-22)
        # Then col 23 was originally 25 (org), col 24 was 26 (asn), col 25 was 27 (?), col 26 was 28 (host)
        # Looking at the actual values:
        # r[23] = '49.839' (this should be lat)
        # r[24] = '24.0191' (this should be lon)
        # r[25] = 'NVTOV "SOLVER"' (this is actually org)
        # r[26] = 'Science Production Enterprise Solver Ltd' (this is actually org description or similar)
        # r[27] = 'AS15461 NVTOV "SOLVER"' (this is ASN)
        # r[28] = '' (real isp?)
        # r[29] = '194.44.38.196' (this is reverse_dns? or host?)
        # r[30] = 'medium' (confidence)
        # r[31] = 'Family=axis-mjpeg,...' (notes)
        # r[32] = 'disc_63943' (csv_id)

        # So the shift is: cols 23,24 were lat,lon (these are correct values just in wrong col)
        # cols 25-32 were org, asn, reverse_dns, host, confidence, notes, csv_id
        # Wait there are only 32 cols before address/geo_source were added
        # The row had 33 cols originally, so cols 23..32 mapped to old lat..csv_id
        # When we added address (col 23) and geo_source (col 26), the original lat/lon ended up at col 24/25
        # And old org ended up at col 27/28 etc.

        # So the FIX: move col 23 to lat, col 24 to lon, and shift everything from 25 onward to 26 onward
        # We "insert" two empty cells at index 23, 24? No, we need to:
        # 1. Keep r[23] as lat (it's the real lat)
        # 2. Keep r[24] as lon (it's the real lon)
        # 3. r[25..32] becomes new_r[27..34] (shift by +2)
        # 4. new_r[25] = '' (geo_source empty)
        # 5. new_r[26] = '' (isp empty, was previously r[27] which was old isp)

        # But that loses isp, org info. So better: keep the shifted data.
        # Maybe accept the loss.

        # Actually wait — let's think again. The headers now have:
        # idx(0), project_name(1), url(2), lsu(3), type(4), auth_required(5),
        # auth_user(6), auth_pass(7), enabled(8), live_status(9), http_status(10),
        # content_type(11), server_header(12), page_title(13), description(14),
        # category(15), likely_subject(16), brand(17), model(18),
        # country(19), region(20), city(21), zip(22),
        # address(23), lat(24), lon(25), geo_source(26),
        # isp(27), org(28), asn(29), reverse_dns(30), host(31), confidence(32), notes(33), csv_id(34)

        # In a CORRECT row of 35 cols:
        # - cols 0-18: standard fields
        # - 19-22: country/region/city/zip
        # - 23: address (text or empty)
        # - 24: lat (number)
        # - 25: lon (number)
        # - 26: geo_source (text tag)
        # - 27: isp
        # - 28: org
        # - 29: asn
        # - 30: reverse_dns
        # - 31: host
        # - 32: confidence
        # - 33: notes
        # - 34: csv_id

        # In the BROKEN row, original 33-col layout (no address/geo_source) had:
        # - cols 0-22: same as now
        # - 23: lat
        # - 24: lon
        # - 25: isp
        # - 26: org
        # - 27: asn
        # - 28: reverse_dns
        # - 29: host
        # - 30: confidence
        # - 31: notes
        # - 32: csv_id

        # When address and geo_source columns were INSERTED between zip (22) and lat (23):
        # The old cols 23-32 should have been pushed to cols 25-34, but they weren't (the file
        # got partially rewritten somewhere). So:
        # - new col 23 (address) has old col 23 (lat) value: '49.839'
        # - new col 24 (lat) has old col 24 (lon) value: '24.0191'
        # - new col 25 (lon) has old col 25 (isp) value: 'NVTOV "SOLVER"'
        # - new col 26 (geo_source) has old col 26 (org) value: 'Science Production Enterprise Solver Ltd'
        # - new col 27 (isp) has old col 27 (asn) value: 'AS15461 NVTOV "SOLVER"'
        # - new col 28 (org) has old col 28 (reverse_dns) value: ''
        # - new col 29 (asn) has old col 29 (host) value: '194.44.38.196'
        # - new col 30 (reverse_dns) has old col 30 (confidence) value: 'medium'
        # - new col 31 (host) has old col 31 (notes) value: 'Family=axis-mjpeg,...'
        # - new col 32 (confidence) has old col 32 (csv_id) value: 'disc_63943'
        # - new col 33, 34: missing (notes, csv_id)

        # FIX: rebuild cols 23-34 from cols 25-32 (shift left by 2)
        # But we lose the lat/lon which is in cols 23,24!

        # So the proper fix:
        # - Keep col 23 (lat), col 24 (lon)
        # - Move col 25..32 back to col 27..34 (shift right by 2)
        # - Set col 25 (lon) to old col 24 (already there)... wait col 24 is lon. col 25 is also lon position now
        # - Set col 23 (address) = '' (we lost it)
        # - Set col 26 (geo_source) = '' (we lost it)
        # - col 25 should be lon = r[24]
        # - col 27 should be isp = r[25]
        # - col 28 should be org = r[26]
        # - col 29 should be asn = r[27]
        # - col 30 should be reverse_dns = r[28]
        # - col 31 should be host = r[29]
        # - col 32 should be confidence = r[30]
        # - col 33 should be notes = r[31]
        # - col 34 should be csv_id = r[32]

        new_r = list(r[:23])  # cols 0-22
        new_r.append('')  # 23 = address (lost)
        new_r.append(r[23])  # 24 = lat (was wrongly in col 23)
        new_r.append(r[24])  # 25 = lon (was wrongly in col 24)
        new_r.append('')  # 26 = geo_source (lost)
        new_r.append(r[25])  # 27 = isp
        new_r.append(r[26])  # 28 = org
        new_r.append(r[27])  # 29 = asn
        new_r.append(r[28] if len(r) > 28 else '')  # 30 = reverse_dns
        new_r.append(r[29] if len(r) > 29 else '')  # 31 = host
        new_r.append(r[30] if len(r) > 30 else '')  # 32 = confidence
        new_r.append(r[31] if len(r) > 31 else '')  # 33 = notes
        new_r.append(r[32] if len(r) > 32 else '')  # 34 = csv_id

        new_rows.append(new_r)
        fixed += 1
    else:
        new_rows.append(r)

print(f'fixed: {fixed} of {len(rows)-1}')

# Write back
tmp = CSV_PATH + '.tmp'
with open(tmp, 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
    for r in new_rows:
        w.writerow(r)
os.replace(tmp, CSV_PATH)
print('done')
