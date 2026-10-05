"""
Classify every cam row into visibility: public | private | unknown

Evaluation order (first match wins):

HARD private (exposure evidence - wins even over public provenance):
  P1 creds       - BOTH creds present, sane (not column-shift fragments), real
                   stream URL, AND (bare-IP host OR no public provenance)
  P4 exposed-IP  - bare-IP host + cam exposure evidence (rtsp/cam ports/paths)
                   + category not in public set
  P3 nvr         - NVR/DVR signature in title/name + exposure + no provenance

PUBLIC explicit declaration:
  U1 subject     - likely_subject declares "Live public camera" / "Public camera"

CURATED private (beats generic provenance):
  P7 ipcam-name  - "City IP cam (vendor)" / insecam naming convention
  P2a category   - category == 'private' (curated)

PUBLIC provenance (generic sources):
  U2 csv_id      - source prefix in known-public set (tv, disc, occtv, fl, ...)
  U3 family      - Family=/trafficvision_id=/opencctv_id= markers anywhere in row
                   (handles column-shifted legacy rows)
  U5 host        - known public hostnames (alertcalifornia.org, abckam.com)

SOFT private (only when no public provenance):
  P2  category   - category in {residential} OR indoor WITH corroboration
  P5             - category == 'surveillance'
  P6             - strong indoor/private keywords in text

PUBLIC category (last):
  U4             - category in clearly-public set

ELSE: unknown -> resolved later by poster scene analysis

Writes: visibility column into the CSV (atomic replace) + docs/VISIBILITY_REPORT.md
"""
import csv
import os
import re
import collections
from pathlib import Path

CSV_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')
REPORT_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\docs\VISIBILITY_REPORT.md')

# ---- rule sets ----------------------------------------------------------

PUBLIC_CSV_PREFIXES = {
    'tv', 'disc', 'occtv', 'fl', 'transtar', 'az', 'africam', 'kenyawebcam',
    'cam', 'sr', 'd', 'high', 'trafficvision',
}
PUBLIC_CSV_RE = re.compile(r'^(511ny_|[0-9]+$)')

LIKELY_PUBLIC_SUBJECTS = {'live public camera', 'public camera'}

# known public hostnames (ingested directly, csv_id empty)
PUBLIC_HOSTS = ('alertcalifornia.org', 'abckam.com')

# content markers identifying public aggregator provenance anywhere in the row
PUBLIC_CONTENT_MARKERS = (
    'family=', 'trafficvision_id=', 'opencctv_id=', 'fl511; systemsourceid',
    'source=argus', 'source=opencctv', 'source=live_env', 'source=caltrans',
    'argus_public', 'feratel:', 'webcamtaxi-',
    # Phase 4 FP fixes: provenance that sits in shifted/odd columns
    'divas.cloud', 'trafficvision.live',
    'hosted by **opencctv', 'hosted by **argus public',
)

# source-id patterns (disc_166841, tv_1234, ...) found in ANY column —
# column-shifted legacy rows park their csv_id in notes/auth fields
PROV_ANY_RE = re.compile(r'\b(?:disc|tv|occtv|fl|transtar|az|africam)_[0-9]{3,}\b')

# real credential strings are short and contain no path/separator junk;
# shifted rows park fragments ('US', 'California', URLs, 'True') in auth cols
CRED_RE = re.compile(r'^[A-Za-z0-9._@!$%#+^-]{1,40}$')

PUBLIC_CATEGORIES = {
    'traffic', 'public', 'scenic', 'water-gauge', 'mountain', 'nature',
    'weather-sky', 'city', 'ski', 'water', 'beach', 'weather', 'aviation',
    'lake', 'airport', 'river', 'port', 'intersection', 'harbor', 'rail',
    'coast', 'marina', 'street', 'forest', 'volcano', 'wildlife', 'airfield',
    'city-skyline', 'bridge', 'boats', 'observatory', 'surf', 'dam', 'zoo',
    'ferry', 'plaza', 'canal-lock', 'border', 'resort', 'glacier-polar',
    'highway', 'ship-onboard', 'landmark', 'satellite', 'tourist', 'pier',
    'promenade', 'waterfall', 'tropical', 'golf', 'station', 'space-earth',
    'desert', 'island', 'tourism', 'sports-field', 'religious-site',
    'boardwalk', 'tunnel', 'amusement', 'space', 'rural', 'open-water',
    'public-network-camera', 'opencctv (state511)',
    'caltrans (california dot)',
}

# category private/residential: private without corroboration
# category indoor: needs corroboration (streaming radio has junk 'indoor' category)
PRIVATE_CATEGORIES = {'private', 'residential'}
STREAM_TYPES = {'hls', 'youtube', 'mp4', 'video', 'iframe', 'video-h264'}

# exposure evidence for bare-IP cams
EXPOSED_PORT_RE = re.compile(
    r':(554|8554|8080|8081|8082|8888|8000|8001|9000|7000|10000)([:/]|$)')
EXPOSED_PATH_RE = re.compile(
    r'(mjpg|videostream|snapshot\.cgi|webcapture|/cgi-bin/|live\.jpg|fmp2|'
    r'axis-cgi|isapi|/snap\.jpg|/image\.cgi|video\.cgi|/cam\.jpg|viewer\.cgi|'
    r'stream\.asf|/ch\d+/|/chn\d+/|channel=)', re.I)

# NVR signature - matched against title/name/description ONLY (never URL params:
# 'dvr=false' query params caused false positives)
NVR_RE = re.compile(r'netsurveillance|\bnvr\b|\bdvr\b|webcapture\.jpg', re.I)

# strong private keywords - only used when provenance is NOT public
PRIVATE_KW_RE = re.compile(
    r'\b(baby\s+monitor|nursery|bedroom|living\s+room|kitchen|doorbell|'
    r'home\s+security|backyard|front\s+door|apartment|home\s+interior|'
    r'indoor\s+cam|security\s+cam|pet\s+cam|webcam\s+at\s+home|'
    r'house\s+cam|my\s+house|private\s+home)\b', re.I)

BARE_IP_RE = re.compile(r'^\d{1,3}(\.\d{1,3}){3}$')


def csv_prefix(cid: str) -> str:
    cid = cid.strip()
    if not cid:
        return ''
    m = re.match(r'^([A-Za-z_]+?)[_0-9]', cid)
    if m:
        return m.group(1).lower()
    return cid.lower()


def classify(row):
    """Return (visibility, reason)."""
    cid = (row.get('csv_id') or '').strip()
    pref = csv_prefix(cid)
    cat = (row.get('category') or '').strip().lower()
    host = (row.get('host') or '').strip()
    url = (row.get('url') or '').strip()
    user = (row.get('auth_user') or '').strip()
    pw = (row.get('auth_pass') or '').strip()
    subj = (row.get('likely_subject') or '').strip().lower()
    ctype = (row.get('type') or '').strip().lower()
    title = (row.get('page_title') or '')
    proj = (row.get('project_name') or '')
    desc = (row.get('description') or '')
    notes = (row.get('notes') or '')

    # all-fields blob: content markers survive column-shifted legacy rows
    all_blob = ' '.join([title, proj, desc, notes, host, url, subj,
                         user, pw, cat, ctype]).lower()
    # text blob: name/title/desc/notes only - for NVR + keyword matching
    text_blob = ' '.join([title, proj, desc, notes]).lower()
    # every field value - for source-id provenance (disc_1234 anywhere)
    full_blob = ' '.join((v or '') for v in row.values()).lower()

    is_ip = bool(BARE_IP_RE.match(host)) or bool(BARE_IP_RE.match(
        re.sub(r'^https?://', '', url).split('/')[0].split(':')[0] if url else ''))

    # ---- public provenance (computed once) ----
    prov = None
    if subj in LIKELY_PUBLIC_SUBJECTS:
        prov = 'U1-subject'
    elif pref in PUBLIC_CSV_PREFIXES or PUBLIC_CSV_RE.match(cid or ''):
        prov = 'U2-csv_id'
    elif PROV_ANY_RE.search(full_blob):
        prov = 'U2-csv_id'
    elif any(m in all_blob for m in PUBLIC_CONTENT_MARKERS):
        prov = 'U3-family'
    elif host:
        h = host.lower()
        h = h[4:] if h.startswith('www.') else h
        if any(h.endswith(d) for d in PUBLIC_HOSTS):
            prov = 'U5-host'

    # ---- HARD private ----
    # P1: BOTH creds present, sane-looking (not column-shift fragments),
    # on a real stream URL; bare IP = always private, domain = w/o provenance
    if user and pw and CRED_RE.match(user) and CRED_RE.match(pw) and \
            url.lower().startswith(('http://', 'https://', 'rtsp://')) and \
            (is_ip or not prov):
        return 'private', 'P1-creds'

    # P4: bare IP + exposure evidence + non-public category
    if is_ip and cat not in PUBLIC_CATEGORIES:
        if url.lower().startswith('rtsp') or EXPOSED_PORT_RE.search(url) or \
                EXPOSED_PATH_RE.search(url):
            return 'private', 'P4-exposed-ip'

    # P3: NVR signature in text + exposure + no provenance
    if not prov and NVR_RE.search(text_blob) and \
            (is_ip or EXPOSED_PATH_RE.search(url)):
        return 'private', 'P3-nvr'

    # ---- PUBLIC: explicit declaration ----
    if prov == 'U1-subject':
        return 'public', prov

    # ---- curated private (beats generic csv_id / content provenance) ----
    # P7: exposed-cam naming convention: "City IP cam (vendor)", insecam...
    if re.search(r'\bip cam\b|insecam', text_blob, re.I):
        return 'private', 'P7-ipcam-name'
    # P2a: curated category 'private'
    if cat == 'private':
        return 'private', 'P2-category'

    # ---- PUBLIC provenance (generic sources) ----
    if prov:
        return 'public', prov

    # ---- SOFT private ----
    if cat in PRIVATE_CATEGORIES:
        return 'private', 'P2-category'
    if cat == 'indoor' and (
            is_ip or ctype in ('image', 'mjpeg') or EXPOSED_PATH_RE.search(url)):
        return 'private', 'P2-indoor'
    if cat == 'surveillance':
        return 'private', 'P5-surveillance'
    if PRIVATE_KW_RE.search(text_blob):
        return 'private', 'P6-keyword'

    # ---- PUBLIC category ----
    if cat in PUBLIC_CATEGORIES:
        return 'public', 'U4-category'

    return 'unknown', 'no-rule'


def main():
    with open(CSV_PATH, encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)

    has_vis = 'visibility' in header
    vis_col = header.index('visibility') if has_vis else None

    counts = collections.Counter()
    reasons = collections.Counter()
    reason_vis = {}
    samples = collections.defaultdict(list)

    vis_values = []
    for row in rows:
        if not row:
            vis_values.append(None)
            continue
        if len(row) < len(header):
            row = row + [''] * (len(header) - len(row))
        rec = dict(zip(header, row))
        vis, reason = classify(rec)
        vis_values.append(vis)
        counts[vis] += 1
        reasons[reason] += 1
        reason_vis[reason] = vis
        if len(samples[reason]) < 12:
            samples[reason].append(
                (rec.get('idx'), (rec.get('category') or '')[:14],
                 (rec.get('host') or '')[:26], vis,
                 (rec.get('project_name') or rec.get('page_title') or '')[:60],
                 (rec.get('url') or '')[:60]))

    if has_vis:
        new_header = header
        new_rows = []
        for row, vis in zip(rows, vis_values):
            if not row:
                new_rows.append(row)
                continue
            row = row + [''] * (len(header) - len(row))
            row[vis_col] = vis
            new_rows.append(row)
    else:
        new_header = header + ['visibility']
        new_rows = []
        for row, vis in zip(rows, vis_values):
            if not row:
                new_rows.append(row)
                continue
            row = row + [''] * (len(header) - len(row))
            new_rows.append(row + [vis])

    # --- atomic write ---
    tmp = CSV_PATH.with_suffix('.csv.tmp')
    with open(tmp, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(new_header)
        writer.writerows(new_rows)

    # validate
    with open(tmp, encoding='utf-8', newline='') as f:
        r2 = csv.reader(f)
        h2 = next(r2)
        n2 = sum(1 for _ in r2)
    assert h2 == new_header, 'header mismatch'
    assert n2 == len(rows), f'row count mismatch {n2} != {len(rows)}'
    os.replace(tmp, CSV_PATH)

    # --- report ---
    lines = []
    lines.append('# Visibility classification report (Session 41)\n')
    lines.append(f'- Rows: **{len(rows):,}**')
    lines.append(f'- Column: `visibility` — ' +
                 ', '.join(f'**{k}** {v:,}' for k, v in counts.most_common()))
    lines.append('- Source: `controllable_Webcams.csv` '
                 '(backup: `backups/session_v41_20261003/`)\n')
    lines.append('## Counts per rule\n')
    lines.append('| rule | visibility | rows |')
    lines.append('|---|---|---|')
    for reason, n in reasons.most_common():
        lines.append(f'| {reason} | {reason_vis[reason]} | {n:,} |')
    lines.append('')
    lines.append('## Rule detail (samples)\n')
    for reason, n in reasons.most_common():
        lines.append(f'### {reason} — {n:,} rows\n')
        lines.append('```')
        for s in samples[reason]:
            lines.append(' | '.join(str(x) for x in s))
        lines.append('```\n')
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text('\n'.join(lines), encoding='utf-8')

    print(f'rows: {len(rows):,}')
    for k, v in counts.most_common():
        print(f'  {k:8s} {v:,}')
    print('reasons:')
    for k, v in reasons.most_common():
        print(f'  {k:20s} {v:,}')
    print(f'report: {REPORT_PATH}')


if __name__ == '__main__':
    main()
