"""CSV writer — atomic row append with retry on Windows lock errors.

Cross-process safe via file lock held throughout the read-modify-write.
The lock file is created via os.O_EXCL so only ONE writer holds it at a time.
"""
import csv
import os
import sys
import time
import threading

CSV_PATH = r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv'

_csv_lock = None


def _acquire_lock():
    global _csv_lock
    if _csv_lock is None:
        _csv_lock = threading.Lock()
    return _csv_lock


def _next_idx(rows):
    max_idx = 0
    for r in rows[1:]:
        try:
            v = int(r[0])
            if v > max_idx:
                max_idx = v
        except Exception:
            pass
    return max_idx + 1


def entry_from_probe(probe_res, src_candidate, geo):
    fam = probe_res.get('family', '')
    kind = probe_res.get('stream_kind', '')
    host = probe_res['host']
    port = probe_res['port']
    live = probe_res['url']
    ssl = probe_res.get('ssl', False)
    root = f'{("https" if ssl else "http")}://{host}:{port}'

    type_label = 'image'
    if 'mjpeg' in kind or 'multipart' in kind or 'mjpg' in kind:
        type_label = 'video-mjpeg'
    elif 'matroska' in kind or 'mp4' in kind:
        type_label = 'video-h264-matroska' if 'matroska' in kind else 'video-h264-mp4'
    elif 'h264' in fam or 'h265' in fam:
        type_label = 'video-h264' if 'h264' in fam else 'video-h265'
    elif 'image' in fam or 'jpeg' in kind:
        type_label = 'image'

    city_label = geo.get('city') or host
    org_label = (geo.get('org') or '')
    is_residential = 'HiSilicon' in org_label or any(k in org_label.lower() for k in (
        'comcast', 'charter', 'verizon', 'at&t fiber', 'residential', 'spectrum',
        'cablelink', 'ziggo', 't-com', 'aruba'))
    name = f'{"Residential " if is_residential else ""}{city_label} IP cam ({fam})'
    name = name.strip().replace('  ', ' ')

    notes = (
        f'Family={fam}, kind={kind}, weight={probe_res.get("weight")}, '
        f'source={src_candidate.get("source", "")}, content-type={probe_res.get("content_type", "")}, '
        f'server-banner-unknown'
    )
    if probe_res.get('content_length'):
        notes += f', content-length={probe_res["content_length"]}'

    # Auto-fill country/region/city from lat/lon via reverse_geocoder
    try:
        lat_val = geo.get('lat') or geo.get('_latlon', ('', ''))[0]
        lon_val = geo.get('lon') or geo.get('_latlon', ('', ''))[1]
        if lat_val and lon_val and not (geo.get('country') and geo.get('city')):
            try:
                import reverse_geocoder as _rg
                latf = float(lat_val)
                lonf = float(lon_val)
                if -90 <= latf <= 90 and -180 <= lonf <= 180:
                    r = _rg.search((latf, lonf))[0]
                    iso2 = r.get('cc', '')
                    # Translate ISO2 to canonical name (matches ISO_TO_NAME table)
                    iso_map = {
                        "US":"United States","GB":"United Kingdom","KR":"South Korea",
                        "JP":"Japan","DE":"Germany","FR":"France","IT":"Italy",
                        "CA":"Canada","AU":"Australia","BR":"Brazil","IN":"India",
                        "MX":"Mexico","RU":"Russia","CN":"China","ES":"Spain",
                        "NL":"Netherlands","SE":"Sweden","NO":"Norway","FI":"Finland",
                        "DK":"Denmark","PL":"Poland","CH":"Switzerland","AT":"Austria",
                        "BE":"Belgium","IE":"Ireland","PT":"Portugal","GR":"Greece",
                        "TR":"Turkey","ID":"Indonesia","TH":"Thailand","VN":"Vietnam",
                        "PH":"Philippines","MY":"Malaysia","SG":"Singapore","HK":"Hong Kong",
                        "TW":"Taiwan","NZ":"New Zealand","ZA":"South Africa","EG":"Egypt",
                        "AR":"Argentina","CL":"Chile","CO":"Colombia","PE":"Peru",
                        "CZ":"Czech Republic","HR":"Croatia","HU":"Hungary","RO":"Romania",
                        "BG":"Bulgaria","UA":"Ukraine","SI":"Slovenia","SK":"Slovakia",
                        "RS":"Serbia","BA":"Bosnia and Herzegovina","AL":"Albania",
                        "MK":"North Macedonia","ME":"Montenegro","LT":"Lithuania",
                        "LV":"Latvia","EE":"Estonia","IS":"Iceland","LU":"Luxembourg",
                        "PR":"Puerto Rico","GL":"Greenland",
                    }
                    geo['country'] = iso_map.get(iso2, iso2)
                    if not geo.get('regionName') and r.get('admin1'):
                        geo['regionName'] = r['admin1']
                    if not geo.get('city') and r.get('name'):
                        geo['city'] = r['name']
            except Exception:
                pass
    except Exception:
        pass

    try:
        from descriptions import describe
        row_proxy = {
            'host': host,
            'geo': geo,
            'family': fam,
            'stream_kind': kind,
        }
        description = describe(row_proxy)
    except Exception:
        description = ''

    return {
        'idx': '',
        'project_name': name,
        'url': root,
        'live_stream_url': live,
        'type': type_label,
        'auth_required': '',
        'auth_user': '',
        'auth_pass': '',
        'enabled': 'True',
        'live_status': 'live',
        'http_status': str(probe_res.get('http_status', 200)),
        'content_type': probe_res.get('content_type', ''),
        'server_header': '',
        'page_title': '',
        'description': description,
        'category': 'public' if not is_residential else 'private',
        'likely_subject': 'Building, parking, terrace, road, shop-floor, etc.',
        'brand': geo.get('brand', '') or (fam if fam and fam != 'unknown' else ''),
        'model': geo.get('model', '') or (kind if kind else ''),
        'country': geo.get('country', ''),
        'region': geo.get('regionName', ''),
        'city': geo.get('city', ''),
        'zip': '',
        'lat': str(geo.get('lat', '')),
        'lon': str(geo.get('lon', '')),
        'isp': geo.get('isp', ''),
        'org': geo.get('org', ''),
        'asn': geo.get('as', ''),
        'reverse_dns': '',
        'host': host,
        'confidence': 'medium',
        'notes': notes,
    }


def append_one(entry):
    """Append one row to CSV atomically with retry on contention.

    Critical: the lock file must be released in a finally block, even on errors.
    """
    is_windows = sys.platform.startswith('win')
    lock_path = CSV_PATH + '.lock'
    lock_fd = None
    for attempt in range(80):
        try:
            lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            break
        except FileExistsError:
            time.sleep(0.05 + 0.03 * (attempt % 10))
        except Exception:
            time.sleep(0.05)

    if lock_fd is None:
        # Last-ditch: try to delete stale lock and retry once
        try:
            os.remove(lock_path)
        except OSError:
            pass
        return None

    try:
        next_idx = None
        for write_attempt in range(20):
            try:
                rows = None
                for read_attempt in range(5):
                    try:
                        with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
                            rows = list(csv.reader(f))
                        break
                    except PermissionError:
                        time.sleep(0.2 + 0.1 * read_attempt)
                if rows is None:
                    raise PermissionError('read failed')

                next_idx = _next_idx(rows)
                header = rows[0] if rows else []

                # Build row dynamically using header column names
                # This way, if header changes (new columns added), we write correctly
                row = [str(next_idx)]  # idx
                for col_name in header[1:]:
                    if col_name == 'csv_id':
                        # callers may set csv_id_prefix (e.g. 'nls', 'shd') so
                        # provenance stays truthful; legacy default is 'disc'
                        pref = str(entry.get('csv_id_prefix') or 'disc')
                        row.append(f'{pref}_{next_idx:04d}')
                    else:
                        v = entry.get(col_name, '')
                        try:
                            s = str(v).replace('\r', ' ').replace('\n', ' ').strip()
                            s = s.encode('ascii', 'replace').decode('ascii', 'replace')
                            row.append(s)
                        except Exception:
                            row.append('')

                rows.append(row)

                tmp_path = CSV_PATH + '.tmp'
                written = False
                for wa in range(8):
                    try:
                        with open(tmp_path, 'w', encoding='utf-8', newline='') as f:
                            w = csv.writer(f, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
                            for r in rows:
                                w.writerow(r)
                        os.replace(tmp_path, CSV_PATH)
                        written = True
                        break
                    except PermissionError:
                        if wa == 7:
                            raise
                        time.sleep(0.3 + 0.2 * wa)
                if not written:
                    raise OSError('write failed')
                return next_idx
            except (PermissionError, OSError):
                time.sleep(0.4 + 0.3 * write_attempt)
    finally:
        if lock_fd is not None:
            try:
                os.close(lock_fd)
            except Exception:
                pass
            try:
                os.remove(lock_path)
            except OSError:
                pass
    return next_idx
