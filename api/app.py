"""
eli6-surveillance Flask dashboard backend.

Endpoints:
  GET  /                              dashboard HTML
  GET  /api/cams                      paginated cam list (server-side filter + sort)
  GET  /api/cams/<idx>                single cam details
  GET  /api/stats                     header counters, by-type, by-country, top cities
  GET  /api/health                    system health (CSV, reaper, proxies, daemon)
  GET  /api/health/pid                pid alive check
  GET  /api/geojson                   GeoJSON for Leaflet
  GET  /api/countries                 distinct countries
  GET  /api/regions                   distinct regions for country
  GET  /api/cities                    distinct cities for region
  GET  /api/proxy/mjpeg               image proxy (CORS bypass)
  GET  /api/proxy/hls                 HLS playlist proxy (avoids CORS for HLS)
  GET  /api/satap/proxy               SATAP A4 MP4 proxy (CORS bypass + byte-range)
  GET  /api/satap/poster              SATAP A4 JPEG poster proxy
  GET  /api/transtar/frames           TranStar slideshow frames JSON
  GET  /api/ai/categorize             auto-categorize all cams via TF-IDF + clustering
  GET  /api/ai/insights               generate natural-language insights
  GET  /api/ai/similar/<idx>          find cams similar to <idx>
  GET  /api/ai/search                 smart search (city/IP/coords/URL/keyword)
  GET  /api/ai/hotspots               DBSCAN geo clusters
  GET  /api/ai/snapshot               one-line snapshot of all cams

  POST /api/refresh                   force reload CSV into SQLite

Storage: SQLite for indexed queries. CSV is read on first boot and reloaded on file change.
"""
import csv
import json
import os
import random
import re
import sys
import sqlite3
import threading
import time
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory, abort, Response

# ====== Paths ======
CSV_PATH    = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv')
DB_PATH     = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\cams.db')
DASH_DIR    = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\web_viewer')
PROXY_FL511   = 'http://127.0.0.1:8770'
PROXY_SKYLINE = 'http://127.0.0.1:8771'

app = Flask(__name__, static_folder=str(DASH_DIR / 'static'), static_url_path='/static')


# ====== Gzip compression for large responses ======
import gzip as _gzip
import io as _io
import re as _re_static

_STATIC_RE = _re_static.compile(r'\.(js|css|html|json|svg|ico|txt|map)$', _re_static.IGNORECASE)
_API_RE = _re_static.compile(r'^/api/')

@app.after_request
def _gzip_response(resp):
    """Compress large text responses for ~70% bandwidth reduction."""
    try:
        # Don't double-compress
        if resp.headers.get('Content-Encoding'):
            return resp
        # Skip small responses
        clen = resp.calculate_content_length()
        if clen is None or clen < 1024:
            return resp
        # Check if client accepts gzip
        accept = request.headers.get('Accept-Encoding', '')
        if 'gzip' not in accept:
            return resp
        # Only compress text-ish content
        ct = resp.headers.get('Content-Type', '')
        if not (ct.startswith('text/') or ct.startswith('application/json') or
                ct.startswith('application/javascript') or 'json' in ct):
            return resp
        # Skip already-compressed
        if 'compress' in ct or 'gzip' in ct or 'zip' in ct:
            return resp
        # Compress
        body = resp.get_data()
        if not body:
            return resp
        buf = _io.BytesIO()
        with _gzip.GzipFile(fileobj=buf, mode='wb', compresslevel=5) as gz:
            gz.write(body)
        gz_data = buf.getvalue()
        # Only use compression if it actually saved bytes
        if len(gz_data) < len(body) * 0.95:
            resp.set_data(gz_data)
            resp.headers['Content-Encoding'] = 'gzip'
            resp.headers['Content-Length'] = str(len(gz_data))
            resp.headers['Vary'] = 'Accept-Encoding'
    except Exception:
        pass
    return resp


# ====== fl511 id lookup ======
# Map CSV idx -> fl511 image_id (used by player.js to pass cam_id to /stream_url)
_FLT_IDX_TO_CAMID = {}
_FLT_IDX_TO_CAMID_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\fl511_idx_to_camid.json')
try:
    if _FLT_IDX_TO_CAMID_PATH.exists():
        with open(_FLT_IDX_TO_CAMID_PATH, encoding='utf-8') as _f:
            data = json.load(_f)
            _FLT_IDX_TO_CAMID = {int(k): int(v) for k, v in data.items()}
        print(f'[eli6-d] loaded {len(_FLT_IDX_TO_CAMID)} fl511 cam_id mappings')
except Exception as _e:
    print(f'[eli6-d] fl511 mapping load error: {_e}')


# Cache-Control for static assets
@app.after_request
def _add_cache_headers(resp):
    """Cache static assets for 1 day, API responses no-cache."""
    path = request.path
    if _STATIC_RE.search(path):
        resp.headers.setdefault('Cache-Control', 'public, max-age=86400')
    elif _API_RE.match(path):
        resp.headers.setdefault('Cache-Control', 'no-store, must-revalidate')
    return resp

# ====== In-memory state ======
_LOCK = threading.RLock()
_CSV_MTIME = 0
_CAMS = []                  # list of all cams (full dicts)
_CAMS_BY_ID = {}            # idx -> cam
_DB_CONN = None             # SQLite connection
_DB_READY = False
_LAST_LOAD_TS = 0


# ====== Helpers ======
def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _detect_type(url, declared_type=''):
    if not url and not declared_type:
        return 'other'
    u = (url or '').lower()
    t = (declared_type or '').lower()
    if 'mjpeg' in t or 'image' in t:
        return 'mjpeg'
    if 'mp4' in t or 'video-mp4' in t:
        return 'mp4'
    if '.m3u8' in u or 'm3u8' in u:
        return 'hls'
    if '.mp4' in u:
        return 'mp4'
    if 'youtube.com' in u or 'youtu.be' in u:
        return 'youtube'
    if '.jpg' in u or '.jpeg' in u or 'image' in t:
        return 'mjpeg'
    if 'video' in t or 'm3u8' in t:
        return 'hls'
    return 'other'


def _ensure_db(force_reload=False):
    """Create SQLite schema and load CSV if needed.
    Auto-reload is DISABLED — other processes (reaper, dedup, ingestors)
    touch the CSV constantly which would trigger expensive reloads on every
    API call. Use force_reload=True (via /api/refresh) for explicit reloads.
    """
    global _DB_CONN, _DB_READY, _CSV_MTIME, _CAMS, _CAMS_BY_ID, _LAST_LOAD_TS
    with _LOCK:
        if not DB_PATH.parent.exists():
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        if _DB_CONN is None:
            _DB_CONN = sqlite3.connect(str(DB_PATH), check_same_thread=False)
            _DB_CONN.row_factory = sqlite3.Row
            _DB_CONN.execute("PRAGMA journal_mode=WAL")
            _DB_CONN.execute("PRAGMA synchronous=NORMAL")

        # MIGRATION: Add new columns to existing cams table if missing
        # Must run BEFORE executescript() that creates indices on new columns
        try:
            cur_cols = [r[1] for r in _DB_CONN.execute("PRAGMA table_info(cams)").fetchall()]
            for col, typedef in (('road', 'TEXT'), ('location_precision', 'TEXT')):
                if cur_cols and col not in cur_cols:
                    try:
                        _DB_CONN.execute(f"ALTER TABLE cams ADD COLUMN {col} {typedef}")
                        _DB_CONN.commit()
                    except Exception:
                        pass
        except Exception:
            pass

        # Schema
        _DB_CONN.executescript("""
        CREATE TABLE IF NOT EXISTS cams (
          idx INTEGER PRIMARY KEY,
          name TEXT,
          url TEXT,
          live TEXT,
          type TEXT,
          auth INTEGER,
          auth_user TEXT,
          auth_pass TEXT,
          enabled INTEGER,
          live_status TEXT,
          http_status INTEGER,
          content_type TEXT,
          server_header TEXT,
          page_title TEXT,
          description TEXT,
          category TEXT,
          likely_subject TEXT,
          brand TEXT,
          model TEXT,
          country TEXT,
          region TEXT,
          city TEXT,
          zip TEXT,
          address TEXT,
          via TEXT,
          road TEXT,
          location_precision TEXT,
          lat REAL,
          lon REAL,
          geo_source TEXT,
          isp TEXT,
          org TEXT,
          asn TEXT,
          reverse_dns TEXT,
          host TEXT,
          confidence REAL,
          notes TEXT,
          full_row TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_country  ON cams(country);
        CREATE INDEX IF NOT EXISTS idx_region   ON cams(region);
        CREATE INDEX IF NOT EXISTS idx_city     ON cams(city);
        CREATE INDEX IF NOT EXISTS idx_type     ON cams(type);
        CREATE INDEX IF NOT EXISTS idx_status   ON cams(live_status);
        CREATE INDEX IF NOT EXISTS idx_host     ON cams(host);
        CREATE INDEX IF NOT EXISTS idx_geo      ON cams(lat, lon);
        CREATE INDEX IF NOT EXISTS idx_isp      ON cams(isp);
        CREATE INDEX IF NOT EXISTS idx_category ON cams(category);
        CREATE INDEX IF NOT EXISTS idx_idx      ON cams(idx);
        CREATE INDEX IF NOT EXISTS idx_road     ON cams(road);
        CREATE INDEX IF NOT EXISTS idx_precision ON cams(location_precision);

        CREATE VIRTUAL TABLE IF NOT EXISTS cams_fts USING fts5(
          idx UNINDEXED,
          name,
          city,
          region,
          country,
          host,
          url,
          live,
          category,
          isp,
          notes,
          address,
          road,
          content='cams',
          content_rowid='idx'
        );
        """)
        _DB_CONN.commit()

        # Decide if we need to load CSV
        try:
            mtime = CSV_PATH.stat().st_mtime
        except OSError:
            return
        # MIGRATION: Add new columns to existing cams table if missing
        # (avoids dropping and recreating the 500MB+ DB)
        try:
            cur_cols = [r[1] for r in _DB_CONN.execute("PRAGMA table_info(cams)").fetchall()]
            for col, typedef in (('road', 'TEXT'), ('location_precision', 'TEXT')):
                if col not in cur_cols:
                    try:
                        _DB_CONN.execute(f"ALTER TABLE cams ADD COLUMN {col} {typedef}")
                        _DB_CONN.commit()
                    except Exception:
                        pass
            # Add new indices if missing (drop+recreate since IF NOT EXISTS handles this)
            try:
                _DB_CONN.execute("CREATE INDEX IF NOT EXISTS idx_road ON cams(road)")
                _DB_CONN.execute("CREATE INDEX IF NOT EXISTS idx_precision ON cams(location_precision)")
            except Exception:
                pass
        except Exception:
            pass
        if _CAMS and not force_reload:
            _DB_READY = True
            return
        # Check if DB has data already
        try:
            count = _DB_CONN.execute('SELECT COUNT(*) FROM cams').fetchone()[0]
        except Exception:
            count = 0
        if count > 0 and _CAMS_BY_ID and not force_reload:
            _CSV_MTIME = mtime
            _DB_READY = True
            return
        if force_reload and _CAMS_BY_ID:
            # Invalidate cache so we re-load
            _CAMS = []
            _CAMS_BY_ID = {}
        _CSV_MTIME = mtime
        print(f'[eli6-d] loading {CSV_PATH} ...', flush=True)

        csv.field_size_limit(2 ** 31 - 1)
        rows = []
        seen_idx = set()
        skipped = 0
        with open(CSV_PATH, encoding='utf-8', errors='replace') as f:
            r = csv.DictReader(f)
            cols = r.fieldnames
            for row in r:
                idx_str = row.get('idx', '').strip()
                if not idx_str or not idx_str.isdigit():
                    skipped += 1
                    continue
                idx = int(idx_str)
                if idx in seen_idx:
                    skipped += 1
                    continue
                seen_idx.add(idx)
                lat = _to_float(row.get('lat', ''))
                lon = _to_float(row.get('lon', ''))
                declared_type = row.get('type', '') or ''
                live = (row.get('live_stream_url', '') or '').strip()
                ctype = _detect_type(live, declared_type)
                def s(v):
                    return (v or '').strip() if v else ''
                cam = {
                    'idx': idx,
                    'name': s(row.get('project_name')),
                    'url': s(row.get('url')),
                    'live': live,
                    'type': ctype,
                    'auth': 1 if row.get('auth_required', '') == 'yes' else 0,
                    'auth_user': s(row.get('auth_user')),
                    'auth_pass': s(row.get('auth_pass')),
                    'enabled': 1 if row.get('enabled', '') in ('1', 'yes', 'true') else 0,
                    'live_status': s(row.get('live_status')),
                    'http_status': _to_int(row.get('http_status', '')),
                    'content_type': s(row.get('content_type')),
                    'server_header': s(row.get('server_header')),
                    'page_title': s(row.get('page_title'))[:300],
                    'description': s(row.get('description'))[:300],
                    'category': s(row.get('category')),
                    'likely_subject': s(row.get('likely_subject')),
                    'brand': s(row.get('brand')),
                    'model': s(row.get('model')),
                    'country': s(row.get('country')),
                    'region': s(row.get('region')),
                    'city': s(row.get('city')),
                    'zip': s(row.get('zip')),
                    'address': s(row.get('address'))[:300],
                    'road': s(row.get('road'))[:100],
                    'location_precision': s(row.get('location_precision'))[:50],
                    'lat': lat,
                    'lon': lon,
                    'geo_source': s(row.get('geo_source')),
                    'isp': s(row.get('isp')),
                    'org': s(row.get('org')),
                    'asn': s(row.get('asn')),
                    'reverse_dns': s(row.get('reverse_dns')),
                    'host': s(row.get('host')),
                    'confidence': _to_float(row.get('confidence', '')) or 0,
                    'notes': s(row.get('notes'))[:500],
                }
                cam['_row'] = row  # keep full original row
                rows.append(cam)

        # Bulk insert into SQLite
        cur = _DB_CONN.cursor()
        cur.execute('DELETE FROM cams')
        cur.execute('DELETE FROM cams_fts')
        cols_db = [c for c in rows[0].keys() if c != '_row'] + ['full_row']
        placeholders = ','.join(['?'] * len(cols_db))
        BATCH = 2000
        for i in range(0, len(rows), BATCH):
            batch = rows[i:i+BATCH]
            data = []
            for r in batch:
                row_vals = []
                for c in cols_db:
                    if c == 'full_row':
                        row_vals.append(json.dumps({k: v for k, v in r['_row'].items() if v}, ensure_ascii=False))
                    elif c == 'idx':
                        v = r.get('idx')
                        row_vals.append(int(v) if v is not None and str(v).strip().isdigit() else None)
                    elif c in ('http_status', 'auth', 'enabled', 'confidence'):
                        v = r.get(c)
                        try:
                            row_vals.append(int(v) if v is not None and str(v).strip() != '' else 0)
                        except (ValueError, TypeError):
                            row_vals.append(0)
                    elif c in ('lat', 'lon'):
                        v = r.get(c)
                        try:
                            row_vals.append(float(v) if v is not None and str(v).strip() != '' else None)
                        except (ValueError, TypeError):
                            row_vals.append(None)
                    else:
                        v = r.get(c, '')
                        row_vals.append(v if v is not None else '')
                data.append(tuple(row_vals))
            cur.executemany(f'INSERT INTO cams ({",".join(cols_db)}) VALUES ({placeholders})', data)
        # FTS insert — note: FTS5 content table needs to be populated
        cur.execute("INSERT INTO cams_fts(cams_fts) VALUES('rebuild')")
        _DB_CONN.commit()
        # Touch DB file so DB mtime > CSV mtime (skips future auto-reloads)
        try:
            os.utime(str(DB_PATH), None)
        except OSError:
            pass

        _CAMS = rows
        _CAMS_BY_ID = {c['idx']: c for c in _CAMS}
        _LAST_LOAD_TS = time.time()
        _DB_READY = True
        print(f'[eli6-d] loaded {len(_CAMS)} cams (skipped {skipped} bad/duplicate rows)', flush=True)


def _to_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _cam_to_dict(row, lite=False):
    """Convert SQLite Row to API dict. lite=True skips bulky fields for grid view."""
    if lite:
        # Minimal dict for grid: ~12 fields, ~250 bytes per row
        d = {
            'idx': row['idx'],
            'name': row['name'] or '',
            'live': row['live'] or '',
            'type': row['type'] or 'other',
            'country': row['country'] or '',
            'region': row['region'] or '',
            'city': row['city'] or '',
            'lat': row['lat'],
            'lon': row['lon'],
            'host': row['host'] or '',
            'road': row['road'] or '',
            'location_precision': row['location_precision'] or '',
        }
        # fl511 cams: include fl511_id so player can pass to /stream_url
        idx = row['idx']
        if idx in _FLT_IDX_TO_CAMID:
            d['fl511_id'] = _FLT_IDX_TO_CAMID[idx]
        return d
    out = {
        'idx': row['idx'],
        'name': row['name'] or '',
        'url': row['url'] or '',
        'live': row['live'] or '',
        'type': row['type'] or 'other',
        'auth': bool(row['auth']),
        'live_status': row['live_status'] or '',
        'http_status': row['http_status'],
        'category': row['category'] or '',
        'brand': row['brand'] or '',
        'model': row['model'] or '',
        'country': row['country'] or '',
        'region': row['region'] or '',
        'city': row['city'] or '',
        'lat': row['lat'],
        'lon': row['lon'],
        'isp': row['isp'] or '',
        'org': row['org'] or '',
        'asn': row['asn'] or '',
        'host': row['host'] or '',
        'confidence': row['confidence'] or 0,
    }
    out['notes'] = row['notes'] or ''
    out['description'] = row['description'] or ''
    out['page_title'] = row['page_title'] or ''
    out['content_type'] = row['content_type'] or ''
    out['server_header'] = row['server_header'] or ''
    out['geo_source'] = row['geo_source'] or ''
    out['reverse_dns'] = row['reverse_dns'] or ''
    out['road'] = row['road'] or ''
    out['location_precision'] = row['location_precision'] or ''
    return out


# ====== Routes ======
@app.route('/')
def index():
    _ensure_db()
    return send_from_directory(DASH_DIR, 'index.html')


@app.route('/<path:path>')
def static_file(path):
    return send_from_directory(DASH_DIR, path)


@app.route('/api/cams')
def api_cams():
    _ensure_db()
    q = (request.args.get('q') or '').strip()
    ctype = (request.args.get('type') or '').strip()
    country = (request.args.get('country') or '').strip()
    region = (request.args.get('region') or '').strip()
    city = (request.args.get('city') or '').strip()
    status = (request.args.get('status') or '').strip()
    has_geo = request.args.get('has_geo') in ('1', 'true', 'yes')
    sort_by = (request.args.get('sort') or 'idx').strip()
    sort_dir = (request.args.get('dir') or 'asc').strip()
    mode = (request.args.get('mode') or '').strip()  # 'random' | 'stratified' | ''
    seed = request.args.get('seed')  # int seed for reproducible random
    limit = min(int(request.args.get('limit', 1000)), 50000)
    offset = int(request.args.get('offset', 0))

    # Build query
    where = []
    params = []
    if ctype:
        where.append('type = ?'); params.append(ctype)
    if country:
        where.append('country = ?'); params.append(country)
    if region:
        where.append('region = ?'); params.append(region)
    if city:
        where.append('city = ?'); params.append(city)
    if status:
        where.append('live_status = ?'); params.append(status)
    if has_geo:
        where.append('lat IS NOT NULL AND lon IS NOT NULL')
    if not status:
        where.append("live_status = 'live'")
    where_sql = ('WHERE ' + ' AND '.join(where)) if where else ''

    # Smart search: if q has special syntax, route elsewhere. Otherwise, use FTS.
    use_fts = False
    if q:
        # Detect special queries
        if re.match(r'^-?\d+(\.\d+)?\s*[, ]\s*-?\d+(\.\d+)?$', q):
            # coords "lat,lon"
            try:
                parts = re.split(r'[, ]+', q.strip())
                lat, lon = float(parts[0]), float(parts[1])
                # bounding box (~1°)
                where.append('lat BETWEEN ? AND ?'); params.extend([lat - 1, lat + 1])
                where.append('lon BETWEEN ? AND ?'); params.extend([lon - 1, lon + 1])
                where_sql = ('WHERE ' + ' AND '.join(where)) if where else ''
            except ValueError:
                pass
        elif re.match(r'^\d{1,3}(\.\d{1,3}){0,3}$', q.replace(' ', '')):
            # IP address
            ip = q.replace(' ', '')
            where.append('(host LIKE ? OR url LIKE ? OR reverse_dns LIKE ?)')
            escaped = ip.replace('.', '.')
            params.extend([f'%{ip}%', f'%{escaped}%', f'%{ip}%'])
            where_sql = ('WHERE ' + ' AND '.join(where)) if where else ''
        elif q.startswith('near ') or q.startswith('coords '):
            parts = q.split()
            try:
                coords = parts[1].split(',')
                lat, lon = float(coords[0]), float(coords[1])
                where.append('lat BETWEEN ? AND ?'); params.extend([lat - 2, lat + 2])
                where.append('lon BETWEEN ? AND ?'); params.extend([lon - 2, lon + 2])
                where_sql = ('WHERE ' + ' AND '.join(where)) if where else ''
            except (ValueError, IndexError):
                pass
        else:
            # Full-text search
            use_fts = True
            # Sanitize query for FTS5
            fts_q = ' '.join(c for c in re.split(r'\W+', q) if c)
            fts_q = re.sub(r'\b(AND|OR|NOT)\b', '', fts_q, flags=re.IGNORECASE)
            fts_q = fts_q.replace('NEAR', '').strip()
            if fts_q:
                where.append('idx IN (SELECT idx FROM cams_fts WHERE cams_fts MATCH ?)')
                # append wildcard for prefix matching
                fts_q = ' '.join(w + '*' for w in fts_q.split()[:6])
                params.append(fts_q)
                where_sql = ('WHERE ' + ' AND '.join(where)) if where else ''

    # Order by
    allowed_sort = {'idx', 'name', 'country', 'city', 'type', 'live_status', 'confidence', 'lat', 'lon'}
    if sort_by not in allowed_sort:
        sort_by = 'idx'
    if sort_dir not in ('asc', 'desc'):
        sort_dir = 'asc'
    order_sql = f'ORDER BY {sort_by} {sort_dir.upper()}'

    cur = _DB_CONN.cursor()
    # Count
    count_q = f'SELECT COUNT(*) FROM cams {where_sql}'
    cur.execute(count_q, params)
    total = cur.fetchone()[0]
    if total == 0:
        return jsonify({'count': 0, 'returned': 0, 'offset': offset, 'limit': limit, 'cams': [], 'use_fts': use_fts, 'mode': mode or 'default'})

    # Random / stratified picking
    page_cams = None
    if mode == 'random':
        try:
            seed_int = int(seed) if seed else int(time.time())
        except (ValueError, TypeError):
            seed_int = int(time.time())
        rng = random.Random(seed_int)
        # Always fetch IDs then pick — bounded scan even with million-row DBs.
        tmp_ids = f'SELECT idx FROM cams {where_sql}'
        cur.execute(tmp_ids, params)
        all_idx = [r[0] for r in cur.fetchall()]
        if not all_idx:
            return jsonify({'count': total, 'returned': 0, 'offset': 0, 'limit': limit, 'cams': [], 'use_fts': use_fts, 'mode': 'random', 'seed': seed_int})
        rng.shuffle(all_idx)
        picked_idx = all_idx[:limit]
        placeholders = ','.join('?' * len(picked_idx))
        cur.execute(f'SELECT * FROM cams WHERE idx IN ({placeholders})', picked_idx)
        # Preserve the random order
        rows_by_idx = {r['idx']: r for r in cur.fetchall()}
        cams = [_cam_to_dict(rows_by_idx[i], lite=True) for i in picked_idx if i in rows_by_idx]
        return jsonify({'count': total, 'returned': len(cams), 'offset': 0, 'limit': limit, 'cams': cams, 'use_fts': use_fts, 'mode': 'random', 'seed': seed_int})

    if mode == 'stratified':
        # Pick one cam per country in round-robin order
        try:
            seed_int = int(seed) if seed else int(time.time())
        except (ValueError, TypeError):
            seed_int = int(time.time())
        rng = random.Random(seed_int)
        # Fetch all matching idx+country
        tmp = f'SELECT idx, country FROM cams {where_sql}'
        cur.execute(tmp, params)
        rows = cur.fetchall()
        if not rows:
            return jsonify({'count': total, 'returned': 0, 'offset': 0, 'limit': limit, 'cams': [], 'use_fts': use_fts, 'mode': 'stratified', 'seed': seed_int})
        # Group idx by country
        by_country = {}
        for idx_val, co in rows:
            by_country.setdefault(co or 'Unknown', []).append(idx_val)
        keys = list(by_country.keys())
        rng.shuffle(keys)
        # Round-robin: take one from each country, cycling
        picked_idx = []
        idx = 0
        attempt = 0
        while len(picked_idx) < limit and attempt < limit * 6:
            k = keys[idx % len(keys)]
            if by_country[k]:
                ri = rng.randrange(len(by_country[k]))
                picked_idx.append(by_country[k].pop(ri))
            idx += 1
            attempt += 1
        if not picked_idx:
            return jsonify({'count': total, 'returned': 0, 'offset': 0, 'limit': limit, 'cams': [], 'use_fts': use_fts, 'mode': 'stratified', 'seed': seed_int})
        rng.shuffle(picked_idx)
        placeholders = ','.join('?' * len(picked_idx))
        cur.execute(f'SELECT * FROM cams WHERE idx IN ({placeholders})', picked_idx)
        rows_by_idx = {r['idx']: r for r in cur.fetchall()}
        cams = [_cam_to_dict(rows_by_idx[i], lite=True) for i in picked_idx if i in rows_by_idx]
        return jsonify({'count': total, 'returned': len(cams), 'offset': 0, 'limit': limit, 'cams': cams, 'use_fts': use_fts, 'mode': 'stratified', 'seed': seed_int})

    # Default: paginated
    # Cap offset to prevent deep scans
    if offset > total:
        offset = max(0, total - limit)
    cur.execute(f'SELECT * FROM cams {where_sql} {order_sql} LIMIT ? OFFSET ?',
                params + [limit, offset])

    # Stream JSON response for large pages (faster TTFB)
    if limit > 1000:
        def _gen():
            import json as _json
            yield '{"count":' + str(total) + ',"offset":' + str(offset) + ',"limit":' + str(limit) + ',"use_fts":' + ('true' if use_fts else 'false') + ',"cams":['
            first = True
            for r in cur:
                if not first:
                    yield ','
                first = False
                yield _json.dumps(_cam_to_dict(r, lite=True), separators=(',', ':'))
            yield ']}'
        return Response(_gen(), mimetype='application/json', headers={'X-Cam-Count': str(total)})
    cams = [_cam_to_dict(r, lite=True) for r in cur.fetchall()]
    return jsonify({
        'count': total,
        'returned': len(cams),
        'offset': offset,
        'limit': limit,
        'cams': cams,
        'use_fts': use_fts,
    })


@app.route('/api/cams/<idx>')
def api_cam(idx):
    _ensure_db()
    cur = _DB_CONN.cursor()
    cur.execute('SELECT * FROM cams WHERE idx = ?', (idx,))
    row = cur.fetchone()
    if not row:
        abort(404)
    cam = _cam_to_dict(row)
    # also load full original row for advanced metadata
    if row['full_row']:
        try:
            cam['full'] = json.loads(row['full_row'])
        except (TypeError, ValueError):
            pass
    return jsonify(cam)


@app.route('/api/stats')
def api_stats():
    _ensure_db()
    cur = _DB_CONN.cursor()

    cur.execute('SELECT COUNT(*) FROM cams')
    total = cur.fetchone()[0]

    cur.execute("SELECT live_status, COUNT(*) FROM cams WHERE live_status IS NOT NULL AND live_status != '' GROUP BY live_status")
    by_status = dict(cur.fetchall())

    cur.execute("SELECT type, COUNT(*) FROM cams WHERE type IS NOT NULL AND type != '' GROUP BY type")
    by_type = dict(cur.fetchall())

    cur.execute("SELECT country, COUNT(*) AS n FROM cams WHERE country IS NOT NULL AND country != '' AND live_status = 'live' GROUP BY country ORDER BY n DESC LIMIT 50")
    by_country = dict(cur.fetchall())

    cur.execute("SELECT region, COUNT(*) AS n FROM cams WHERE region IS NOT NULL AND region != '' AND live_status = 'live' GROUP BY region ORDER BY n DESC LIMIT 30")
    by_region = dict(cur.fetchall())

    cur.execute("SELECT city, COUNT(*) AS n FROM cams WHERE city IS NOT NULL AND city != '' AND live_status = 'live' GROUP BY city ORDER BY n DESC LIMIT 30")
    by_city = dict(cur.fetchall())

    cur.execute("SELECT category, COUNT(*) AS n FROM cams WHERE category IS NOT NULL AND category != '' GROUP BY category ORDER BY n DESC LIMIT 20")
    by_category = dict(cur.fetchall())

    cur.execute("SELECT isp, COUNT(*) AS n FROM cams WHERE isp IS NOT NULL AND isp != '' GROUP BY isp ORDER BY n DESC LIMIT 20")
    by_isp = dict(cur.fetchall())

    cur.execute('SELECT COUNT(*) FROM cams WHERE lat IS NOT NULL AND lon IS NOT NULL')
    with_geo = cur.fetchone()[0]

    cur.execute('SELECT COUNT(DISTINCT country) FROM cams WHERE country IS NOT NULL AND country != ""')
    distinct_countries = cur.fetchone()[0]

    cur.execute('SELECT COUNT(DISTINCT city) FROM cams WHERE city IS NOT NULL AND city != ""')
    distinct_cities = cur.fetchone()[0]

    cur.execute('SELECT COUNT(DISTINCT host) FROM cams WHERE host IS NOT NULL AND host != ""')
    distinct_hosts = cur.fetchone()[0]

    return jsonify({
        'total': total,
        'live': by_status.get('live', 0),
        'dead': by_status.get('dead', 0),
        'auth_required': by_status.get('auth_required', 0),
        'with_geo': with_geo,
        'distinct_countries': distinct_countries,
        'distinct_cities': distinct_cities,
        'distinct_hosts': distinct_hosts,
        'by_type': by_type,
        'by_status': by_status,
        'by_country': by_country,
        'by_region': by_region,
        'by_city': by_city,
        'by_category': by_category,
        'by_isp': by_isp,
        'csv_mtime': _CSV_MTIME,
        'loaded_at': _LAST_LOAD_TS,
    })


@app.route('/api/health')
def api_health():
    out = {'csv': {'path': str(CSV_PATH), 'mtime': _CSV_MTIME, 'rows': len(_CAMS), 'db': str(DB_PATH)}}
    import urllib.request
    out['proxies'] = {}
    for name, url in [('fl511', PROXY_FL511 + '/health'), ('skyline', PROXY_SKYLINE + '/health')]:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                out['proxies'][name] = {'online': True, 'data': json.loads(r.read())}
        except Exception as e:
            out['proxies'][name] = {'online': False, 'error': str(e)[:200]}
    for name, pidfile in [('reaper', 'cam_reaper.pid'), ('token_daemon', 'fl511_token_daemon.pid')]:
        p = CSV_PATH.parent / pidfile
        out[name] = {'pid_file': str(p), 'exists': p.exists()}
    return jsonify(out)


@app.route('/api/health/pid')
def api_health_pid():
    pid_file = request.args.get('file', '')
    if not pid_file or '..' in pid_file:
        abort(400)
    p = Path(pid_file)
    if not p.exists():
        return jsonify({'pid': None, 'exists': False})
    try:
        pid = int(p.read_text().strip())
        import subprocess
        out = subprocess.run(['tasklist', '/FI', f'PID eq {pid}'], capture_output=True, text=True, timeout=2)
        return jsonify({'pid': pid, 'exists': True, 'running': str(pid) in out.stdout})
    except Exception as e:
        return jsonify({'pid': None, 'exists': True, 'error': str(e)})


@app.route('/api/geojson')
def api_geojson():
    _ensure_db()
    ctype = (request.args.get('type') or '').strip()
    status = (request.args.get('status') or 'live').strip()
    country = (request.args.get('country') or '').strip()
    limit = min(int(request.args.get('limit', 50000)), 200000)
    mode = (request.args.get('mode') or '').strip()
    seed = request.args.get('seed') or str(int(time.time()))

    where = ['lat IS NOT NULL', 'lon IS NOT NULL']
    params = []
    if status:
        where.append('live_status = ?'); params.append(status)
    if ctype:
        where.append('type = ?'); params.append(ctype)
    if country:
        where.append('country = ?'); params.append(country)
    where_sql = 'WHERE ' + ' AND '.join(where)

    cur = _DB_CONN.cursor()
    cur.execute(f'SELECT idx, lat, lon FROM cams {where_sql}', params)
    rows = cur.fetchall()
    if mode == 'random' and rows:
        try:
            rng = random.Random(int(seed))
        except (ValueError, TypeError):
            rng = random.Random()
        rng.shuffle(rows)
        rows = rows[:limit]
    elif mode == 'stratified' and rows:
        # group by approx country using lat,lon? we need country col
        cur.execute(f'SELECT idx, lat, lon, country FROM cams {where_sql}', params)
        rows_full = cur.fetchall()
        by_country = {}
        for r in rows_full:
            by_country.setdefault(r['country'] or 'Unknown', []).append((r['idx'], r['lat'], r['lon']))
        try:
            rng = random.Random(int(seed))
        except (ValueError, TypeError):
            rng = random.Random()
        picked = []
        keys = list(by_country.keys())
        rng.shuffle(keys)
        i = 0
        attempts = 0
        while len(picked) < limit and attempts < limit * 6:
            k = keys[i % len(keys)]
            if by_country[k]:
                ri = rng.randrange(len(by_country[k]))
                picked.append(by_country[k].pop(ri))
            i += 1; attempts += 1
        rng.shuffle(picked)
        rows = picked

    picked_idx = [r['idx'] for r in rows]
    if not picked_idx:
        return jsonify({'type': 'FeatureCollection', 'features': [], 'count': 0, 'mode': mode, 'seed': int(seed) if seed and seed.isdigit() else 0})
    placeholders = ','.join('?' * len(picked_idx))
    cur.execute(f'SELECT idx, name, type, country, region, city, lat, lon, live, category, isp FROM cams WHERE idx IN ({placeholders})', picked_idx)
    rows_by_idx = {r['idx']: r for r in cur.fetchall()}
    features = []
    for i in picked_idx:
        r = rows_by_idx.get(i)
        if not r:
            continue
        features.append({
            'type': 'Feature',
            'geometry': {'type': 'Point', 'coordinates': [r['lon'], r['lat']]},
            'properties': {
                'idx': r['idx'], 'name': r['name'], 'type': r['type'],
                'country': r['country'], 'region': r['region'], 'city': r['city'],
                'url': r['live'], 'category': r['category'], 'isp': r['isp'],
            }
        })
    try:
        seed_int = int(seed)
    except (ValueError, TypeError):
        seed_int = 0
    return jsonify({'type': 'FeatureCollection', 'features': features, 'count': len(features), 'mode': mode, 'seed': seed_int})


@app.route('/api/countries')
def api_countries():
    _ensure_db()
    cur = _DB_CONN.cursor()
    cur.execute("SELECT DISTINCT country FROM cams WHERE country IS NOT NULL AND country != '' ORDER BY country")
    return jsonify([r[0] for r in cur.fetchall()])


@app.route('/api/regions')
def api_regions():
    _ensure_db()
    country = (request.args.get('country') or '').strip()
    cur = _DB_CONN.cursor()
    if country:
        cur.execute("SELECT DISTINCT region FROM cams WHERE region IS NOT NULL AND region != '' AND country = ? ORDER BY region", (country,))
    else:
        cur.execute("SELECT DISTINCT region FROM cams WHERE region IS NOT NULL AND region != '' ORDER BY region")
    return jsonify([r[0] for r in cur.fetchall()])


@app.route('/api/cities')
def api_cities():
    _ensure_db()
    country = (request.args.get('country') or '').strip()
    region = (request.args.get('region') or '').strip()
    cur = _DB_CONN.cursor()
    where = ["city IS NOT NULL", "city != ''"]
    params = []
    if country:
        where.append('country = ?'); params.append(country)
    if region:
        where.append('region = ?'); params.append(region)
    cur.execute(f"SELECT DISTINCT city FROM cams WHERE {' AND '.join(where)} ORDER BY city", params)
    return jsonify([r[0] for r in cur.fetchall()])


@app.route('/api/proxy/mjpeg')
def api_proxy_mjpeg():
    """Image/MJPEG proxy — bypasses CORS, with cache-bust."""
    url = request.args.get('u', '').strip()
    if not url or not url.startswith(('http://', 'https://')):
        abort(400, 'invalid url')
    import urllib.request
    import socket
    socket.setdefaulttimeout(8)
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
        })
        with urllib.request.urlopen(req, timeout=8) as r:
            data = r.read()
            ct = r.headers.get('Content-Type', 'image/jpeg')
            if not ct.startswith('image/'):
                # Upstream returned HTML or text — treat as error
                return jsonify({'error': 'upstream returned non-image', 'content_type': ct, 'preview': data[:200].decode(errors='replace')}), 502
            return (data, 200, {
                'Content-Type': ct,
                'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
                'Access-Control-Allow-Origin': '*',
                'X-Proxied-From': url[:120],
            })
    except Exception as e:
        return jsonify({'error': str(e)[:200]}), 502


@app.route('/api/poster/<int:idx>')
def api_poster(idx):
    """Serve the pre-extracted ffmpeg poster for a cam.

    Returns 404 if no poster has been extracted yet (caller should fall
    back to a generated placeholder gradient or skip). We set
    Cache-Control: public, max-age=86400 since posters are static JPEGs
    (a single frame grabbed at extraction time). Negative caching for
    404s (60s) so a 1000-tile grid doesn't hammer the disk.
    """
    import os
    poster_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'web_viewer', 'static', 'posters', f'{idx}.jpg'
    )
    if not os.path.isfile(poster_path):
        # Don't 404-cache forever; if extractor is running, posters appear
        # within an hour. 60s negative cache is a good balance.
        return ('', 404, {
            'Cache-Control': 'public, max-age=60',
            'X-Poster-Status': 'missing',
        })
    # File exists - serve it. Add a tiny query-string-buster so the
    # browser doesn't reuse a cached 404 from before extraction.
    with open(poster_path, 'rb') as f:
        data = f.read()
    # Detect actual format (most are JPEG; some HLS may give WebP/PNG)
    if data[:3] == b'\xff\xd8\xff':
        ct = 'image/jpeg'
    elif data[:8] == b'\x89PNG\r\n\x1a\n':
        ct = 'image/png'
    elif data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        ct = 'image/webp'
    elif data[:6] in (b'GIF87a', b'GIF89a'):
        ct = 'image/gif'
    else:
        ct = 'image/jpeg'  # best guess
    return (data, 200, {
        'Content-Type': ct,
        'Cache-Control': 'public, max-age=86400',
        'X-Poster-Status': 'hit',
        'Content-Length': str(len(data)),
    })


@app.route('/api/proxy/img')
def api_proxy_img():
    """Image poster proxy — fetches an upstream image and returns it.

    Used for HLS tile poster images. Unlike /api/proxy/mjpeg, this:
    - Allows caching (Cache-Control: public, max-age=60)
    - Returns the raw image with proper Content-Type
    - Has a short 5s timeout (posters must be fast)
    - If upstream is .m3u8, also tries the .jpg variant

    Caching: We rely on upstream cache-busting (most HLS cams have
    timestamps in their snapshot URLs). The client also appends ?t=
    for belt-and-suspenders.
    """
    url = request.args.get('u', '').strip()
    if not url or not url.startswith(('http://', 'https://')):
        abort(400, 'invalid url')
    import urllib.request
    import socket
    import re as _re
    socket.setdefaulttimeout(5)
    # If the URL is an m3u8, derive a .jpg variant
    if _re.search(r'\.m3u8(\?|$)', url, _re.IGNORECASE):
        jpg_url = _re.sub(r'\.m3u8(\?.*)?$', r'.jpg\1', url)
        try:
            req = urllib.request.Request(jpg_url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                'Cache-Control': 'no-cache',
            })
            with urllib.request.urlopen(req, timeout=4) as r:
                data = r.read()
                ct = r.headers.get('Content-Type', 'image/jpeg')
                if ct.startswith('image/') and len(data) > 500:
                    return (data, 200, {
                        'Content-Type': ct,
                        'Cache-Control': 'public, max-age=60',
                        'Access-Control-Allow-Origin': '*',
                        'X-Proxied-From': jpg_url[:120],
                    })
        except Exception:
            pass  # fall through to original URL
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Cache-Control': 'no-cache',
        })
        with urllib.request.urlopen(req, timeout=5) as r:
            data = r.read()
            ct = r.headers.get('Content-Type', 'image/jpeg')
            if not ct.startswith('image/'):
                return jsonify({'error': 'upstream returned non-image', 'content_type': ct, 'preview': data[:200].decode(errors='replace')}), 502
            return (data, 200, {
                'Content-Type': ct,
                'Cache-Control': 'public, max-age=60',
                'Access-Control-Allow-Origin': '*',
                'X-Proxied-From': url[:120],
            })
    except Exception as e:
        return jsonify({'error': str(e)[:200]}), 502


@app.route('/api/proxy/hls')
def api_proxy_hls():
    """HLS proxy — bypasses CORS for HLS m3u8 manifests AND segments.

    When hls.js loads a manifest from /api/proxy/hls?u=ORIGINAL_URL it
    expects the manifest's relative segment URLs to also be loadable from
    the same origin. We rewrite every relative segment/sub-playlist URL
    in the manifest to also go through /api/proxy/hls (and forward to
    the original server), so all .m3u8/.ts/.mp4 requests hit our proxy
    with proper CORS headers.

    Manifest rewriting: relative URL → /api/proxy/hls?u=<absolute URL>
    """
    url = request.args.get('u', '').strip()
    if not url or not url.startswith(('http://', 'https://')):
        abort(400, 'invalid url')
    import urllib.request
    import socket
    import re as _re
    from urllib.parse import urljoin, quote
    socket.setdefaulttimeout(10)
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) eli6-surveillance/1.0',
            'Accept': 'application/vnd.apple.mpegurl, */*',
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            data = r.read()
            ct = r.headers.get('Content-Type', '').lower()
            # If the body is an m3u8 manifest, rewrite relative URLs
            is_manifest = (
                b'#EXTM3U' in data or
                b'#EXT-X' in data or
                'mpegurl' in ct or
                'vnd.apple' in ct
            )
            if is_manifest:
                try:
                    text = data.decode('utf-8', errors='replace')
                    # Compute base URL (used for absolute resolution)
                    if url.endswith('.m3u8') or url.endswith('.m3u') or url.endswith('/'):
                        base = url.rsplit('/', 1)[0] + '/'
                    else:
                        base = url + '/'
                    # Helper: resolve relative URL against base
                    def _resolve_and_proxy(maybe_rel):
                        u = maybe_rel.strip()
                        if not u:
                            return u
                        if u.startswith(('http://', 'https://')):
                            abs_url = u
                        elif u.startswith('/'):
                            # Absolute path: prepend origin
                            from urllib.parse import urlparse
                            p = urlparse(url)
                            abs_url = f'{p.scheme}://{p.netloc}{u}'
                        else:
                            abs_url = urljoin(base, u)
                        # Encode into our proxy URL
                        return f'/api/proxy/hls?u={quote(abs_url, safe="")}'
                    # 1) Rewrite #EXT-X-MAP:URI="..."
                    def _repl_quoted(m):
                        inner = m.group(1)
                        return f'URI="{_resolve_and_proxy(inner)}"'
                    text = _re.sub(r'URI="([^"]+)"', _repl_quoted, text)
                    # 2) Rewrite #EXT-X-KEY:URI="..." (encryption key)
                    text = _re.sub(r'(URI=")([^"]+)(")', lambda m: m.group(1) + _resolve_and_proxy(m.group(2)) + m.group(3) if m.group(2) and not m.group(2).startswith('/api/') else m.group(0), text)
                    # 3) Rewrite each non-comment line that references a media file
                    def _repl_line(m):
                        line = m.group(1).strip()
                        if not line:
                            return m.group(0)
                        if line.startswith('/api/'):
                            return m.group(0)  # already proxied
                        if line.startswith(('http://', 'https://')):
                            # Already absolute — route through proxy too (for CORS)
                            return f'/api/proxy/hls?u={quote(line, safe="")}'
                        return _resolve_and_proxy(line)
                    text = _re.sub(r'(?m)^([^\n#][^\n]*\.(?:m3u8|m3u|ts|m4s|mp4|aac|m4a|vtt|webvtt|key|aes|jpg|png)[^\n]*)$',
                                   _repl_line, text)
                    data = text.encode('utf-8')
                except Exception as re_err:
                    print(f'[proxy/hls] rewrite err: {re_err}', flush=True)
            if not ct:
                ct = 'application/vnd.apple.mpegurl'
            return (data, 200, {
                'Content-Type': ct,
                'Cache-Control': 'no-store',
                'Access-Control-Allow-Origin': '*',
            })
    except Exception as e:
        return jsonify({'error': str(e)[:200]}), 502


@app.route('/api/proxy/kcscout/token')
def api_kcscout_token():
    """Proxy: fetch a Wowza securetoken from kcscout.net's DataProvider.asmx.

    Note: kcscout's wowza server IP-restricts tokens to the IP that requested
    the token. Since this proxy runs on our server (not the user's browser),
    the resulting token may only work for users on the same network as our
    server. The dashboard tries multiple fallback paths.
    """
    file_path = request.args.get('file', '').strip()
    if not file_path or '/' not in file_path:
        abort(400, 'invalid file path (expected app/file)')
    import urllib.request as ur
    import socket
    socket.setdefaulttimeout(10)
    try:
        payload = json.dumps({'file': file_path}).encode('utf-8')
        req = ur.Request(
            'https://www.kcscout.net/DataProvider.asmx/GetVideoParams',
            data=payload,
            headers={
                'Content-Type': 'application/json; charset=utf-8',
                'User-Agent': 'Mozilla/5.0 eli6-surveillance/1.0',
                'X-Requested-With': 'XMLHttpRequest',
            },
            method='POST',
        )
        with ur.urlopen(req, timeout=10) as r:
            raw = r.read().decode('utf-8', errors='replace')
            try:
                tok = json.loads(raw).get('d', '')
            except json.JSONDecodeError:
                return jsonify({'error': 'bad upstream response', 'preview': raw[:200]}), 502
        return jsonify({'token': tok, 'file': file_path, 'expires_at_window': 60 * 60})  # token valid ~1h
    except Exception as e:
        return jsonify({'error': str(e)[:200]}), 502


# ====== TranStar frames endpoint (Houston TranStar cam slideshow) ======
# TranStar cams serve JPEG snapshots at /snapshots/cctv/{id}.jpg. Multi-frame cams
# have {id}-2.jpg through {id}-6.jpg. The frames cycle in the browser to simulate
# a live video feed (the images themselves update every few minutes on the server).

# Cache the cam databases
_TRANSTAR_LOCAL_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\transtar_local_cams.json')
_TRANSTAR_REGIONAL_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\transtar_regional_cams.json')
_TRANSTAR_LOCAL = None
_TRANSTAR_REGIONAL = None


def _load_transtar():
    """Load TranStar local + regional cam databases (cached)."""
    global _TRANSTAR_LOCAL, _TRANSTAR_REGIONAL
    if _TRANSTAR_LOCAL is None and _TRANSTAR_LOCAL_PATH.exists():
        with open(_TRANSTAR_LOCAL_PATH, encoding='utf-8') as f:
            _TRANSTAR_LOCAL = json.load(f)
    if _TRANSTAR_REGIONAL is None and _TRANSTAR_REGIONAL_PATH.exists():
        with open(_TRANSTAR_REGIONAL_PATH, encoding='utf-8') as f:
            _TRANSTAR_REGIONAL = json.load(f)
    return _TRANSTAR_LOCAL or [], _TRANSTAR_REGIONAL or []


@app.route('/api/transtar/frames')
def api_transtar_frames():
    """Return slideshow JSON for a TranStar cam.

    Query params:
      - cam_id: numeric ID from cctvSnapshots_out.js (e.g. 1002)
      OR
      - path: regional cam path (e.g. /cctv_construction/txdot/ih-10_at_...)

    Returns:
      {
        "frames": [{"url": "https://www.houstontranstar.org/snapshots/cctv/1002.jpg"},
                   {"url": "https://www.houstontranstar.org/snapshots/cctv/1002-2.jpg"}, ...]
      }
    """
    local_cams, regional_cams = _load_transtar()

    cam_id = request.args.get('cam_id', '').strip()
    path = request.args.get('path', '').strip()

    target = None
    if cam_id:
        try:
            cid_int = int(cam_id)
            for c in local_cams:
                if c['path'].startswith(f'{cid_int}.'):
                    target = c
                    break
        except ValueError:
            pass
    if not target and path:
        for c in regional_cams:
            if c.get('path') == path:
                target = c
                break

    if not target:
        return jsonify({'error': 'cam not found', 'cam_id': cam_id, 'path': path}), 404

    frame_count = target.get('frame_count', 1)
    if frame_count < 1:
        frame_count = 1
    if frame_count > 12:
        frame_count = 12

    if path:
        # Regional cam: use the `path` field directly (already an absolute path)
        base_url = 'https://traffic.houstontranstar.org' if path.startswith('/') else ''
        frames = [{'url': f'{base_url}{path}'}]
    else:
        # Local cam: build URLs for {id}.jpg, {id}-2.jpg, ...
        # Strip ".jpg" from path
        base = target['path'].replace('.jpg', '')
        base_url = 'https://www.houstontranstar.org/snapshots/cctv/'
        frames = [{'url': f'{base_url}{base}.jpg'}]
        for i in range(2, frame_count + 1):
            frames.append({'url': f'{base_url}{base}-{i}.jpg'})

    return jsonify({
        'frames': frames,
        'frame_count': frame_count,
        'cam_name': target.get('name', ''),
        'roadway': target.get('roadway', ''),
        'location': target.get('location', ''),
        'direction': target.get('direction', ''),
    })


# ====== SATAP A4 webcam proxy (Italian A4 toll highway) ======
# SATAP serves short looping .mp4 files at /wp-content/uploads/webcam/a4/{info}.mp4
# Each MP4 is ~85-260KB and is overwritten on the server every ~30s with a fresh
# recording. Browsers can seek (accept-ranges: bytes is supported by the origin),
# so we just proxy the bytes and let the <video> tag handle looping. Cache-bust is
# applied by appending a ?t= timestamp at the player level.

@app.route('/api/satap/proxy')
def api_satap_proxy():
    """MP4 proxy for SATAP A4 webcams. Supports HTTP byte-range so the <video>
    element can seek."""
    url = request.args.get('u', '').strip()
    if not url or 'satapweb.it' not in url or not url.endswith('.mp4'):
        abort(400, 'invalid satap url')
    import urllib.request
    import socket
    socket.setdefaulttimeout(15)
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'video/mp4,video/*;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,it;q=0.8',
        }
        # Forward Range header from the browser so the upstream supports seeking.
        range_hdr = request.headers.get('Range')
        if range_hdr:
            headers['Range'] = range_hdr
        req = urllib.request.Request(url, headers=headers, method='GET')
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read()
            ct = r.headers.get('Content-Type', 'video/mp4')
            status = r.status  # upstream may return 206 Partial Content
            resp_headers = {
                'Content-Type': ct,
                'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Range',
                'Access-Control-Expose-Headers': 'Content-Range, Content-Length, Accept-Ranges',
                'X-Proxied-From': url[:120],
            }
            # Mirror upstream content-range / content-length when present.
            for h in ('Content-Range', 'Content-Length', 'Accept-Ranges'):
                v = r.headers.get(h)
                if v:
                    resp_headers[h] = v
            return (data, status, resp_headers)
    except Exception as e:
        return jsonify({'error': str(e)[:200]}), 502


@app.route('/api/satap/poster')
def api_satap_poster():
    """JPEG poster proxy for SATAP A4 webcams."""
    url = request.args.get('u', '').strip()
    if not url or 'satapweb.it' not in url or not url.endswith('.jpg'):
        abort(400, 'invalid satap jpg url')
    import urllib.request
    import socket
    socket.setdefaulttimeout(8)
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'image/avif,image/webp,image/*,*/*;q=0.8',
        })
        with urllib.request.urlopen(req, timeout=8) as r:
            data = r.read()
            ct = r.headers.get('Content-Type', 'image/jpeg')
            return (data, 200, {
                'Content-Type': ct,
                'Cache-Control': 'no-store',
                'Access-Control-Allow-Origin': '*',
            })
    except Exception as e:
        return jsonify({'error': str(e)[:200]}), 502


# ====== LIVE STREAM MAPPINGS (from TV catalog + autostrade regex) ======
_LIVE_MAP_PATH = Path(r'C:\Users\eli6-admin\Documents\eli6-surveillance\live_cam_mappings_v2.json')
_LIVE_MAP = None
_LIVE_MAP_MTIME = 0


def _load_live_map():
    """Load cam_idx -> live_url mappings from JSON file (cached, hot-reload)."""
    global _LIVE_MAP, _LIVE_MAP_MTIME
    try:
        if not _LIVE_MAP_PATH.exists():
            _LIVE_MAP = {}
            return {}
        mtime = _LIVE_MAP_PATH.stat().st_mtime
        if mtime > _LIVE_MAP_MTIME:
            with open(_LIVE_MAP_PATH, encoding='utf-8') as f:
                data = json.load(f)
            _LIVE_MAP = data.get('mappings', {})
            _LIVE_MAP_MTIME = mtime
            print(f'[LIVE] Loaded {len(_LIVE_MAP):,} live URL mappings', flush=True)
    except Exception as e:
        print(f'[LIVE] load err: {e}', flush=True)
        _LIVE_MAP = {}
    return _LIVE_MAP


@app.route('/api/live_mappings')
def api_live_mappings():
    """Return cam_idx -> live_url mappings for the dashboard."""
    m = _load_live_map()
    return jsonify({
        'count': len(m),
        'mtime': _LIVE_MAP_MTIME,
        'mappings': m,
    })


@app.route('/api/proxy/check_live')
def api_check_live():
    """HEAD test a URL. Returns whether it's a live stream and its type.

    Used by dashboard to test candidate live URLs before switching from static to live.
    """
    url = request.args.get('u', '').strip()
    if not url or not url.startswith(('http://', 'https://')):
        abort(400, 'invalid url')
    import urllib.request
    import socket
    socket.setdefaulttimeout(6)
    result = {
        'url': url,
        'ok': False,
        'type': 'unknown',
        'content_type': '',
        'content_length': None,
        'status': 0,
    }
    try:
        req = urllib.request.Request(url, method='HEAD', headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) eli6-surveillance/1.0',
            'Accept': '*/*',
        })
        with urllib.request.urlopen(req, timeout=6) as r:
            result['status'] = r.status
            result['content_type'] = (r.headers.get('Content-Type') or '').lower()
            cl = r.headers.get('Content-Length')
            if cl and cl.isdigit():
                result['content_length'] = int(cl)
            result['ok'] = r.status == 200
    except urllib.error.HTTPError as e:
        result['status'] = e.code
        # 405 = method not allowed, try GET with Range
        if e.code in (405, 403):
            try:
                req2 = urllib.request.Request(url, method='GET', headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) eli6-surveillance/1.0',
                    'Range': 'bytes=0-2047',
                })
                with urllib.request.urlopen(req2, timeout=6) as r2:
                    result['status'] = r2.status
                    result['content_type'] = (r2.headers.get('Content-Type') or '').lower()
                    result['ok'] = r2.status in (200, 206)
            except Exception:
                pass
    except Exception as e:
        result['error'] = str(e)[:200]
    # Classify
    ct = result['content_type']
    if 'mpegurl' in ct or 'vnd.apple.mpegurl' in ct or '.m3u8' in url.lower():
        result['type'] = 'hls'
    elif 'dash' in ct or 'mpd' in ct or '.mpd' in url.lower():
        result['type'] = 'dash'
    elif ct.startswith('video/') or 'octet-stream' in ct or '.mp4' in url.lower():
        result['type'] = 'mp4'
    elif ct.startswith('image/'):
        result['type'] = 'mjpeg'
    elif 'multipart' in ct or 'x-mixed-replace' in ct:
        result['type'] = 'mjpeg'
    return jsonify(result)


# ====== DIGITRAFFIC PROXY (caches weathercam.digitraffic.fi images, prevents 429) ======
DIGITRAFFIC_PROXY = 'http://127.0.0.1:8772'


@app.route('/api/digitraffic/<preset_id>.jpg')
def api_digitraffic_image(preset_id):
    """Proxy a digitraffic image, with caching."""
    import urllib.request
    import socket
    socket.setdefaulttimeout(10)
    try:
        url = f'{DIGITRAFFIC_PROXY}/img/{preset_id}.jpg'
        req = urllib.request.Request(url, headers={'User-Agent': 'eli6-dashboard/1.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = r.read()
            ct = r.headers.get('Content-Type', 'image/jpeg')
            return (data, 200, {
                'Content-Type': ct,
                'Cache-Control': 'public, max-age=300',
                'Access-Control-Allow-Origin': '*',
            })
    except Exception as e:
        return jsonify({'error': str(e)[:200]}), 502


@app.route('/api/digitraffic/slideshow/<preset_id>.json')
def api_digitraffic_slideshow(preset_id):
    """Return 5 most recent history frames for a digitraffic preset (slideshow mode)."""
    import urllib.request
    import socket
    socket.setdefaulttimeout(10)
    try:
        url = f'{DIGITRAFFIC_PROXY}/slideshow/{preset_id}.json'
        req = urllib.request.Request(url, headers={'User-Agent': 'eli6-dashboard/1.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = r.read()
            # Rewrite frame URLs to go through our /api/digitraffic
            j = data.decode('utf-8') if isinstance(data, bytes) else data
            try:
                parsed = json.loads(j)
                for f in parsed.get('frames', []):
                    f['url'] = f['url'].replace('http://localhost:8772/img/', '/api/digitraffic/')
                j = json.dumps(parsed)
                data = j.encode('utf-8')
            except Exception:
                pass
            return (data, 200, {
                'Content-Type': 'application/json',
                'Cache-Control': 'public, max-age=60',
                'Access-Control-Allow-Origin': '*',
            })
    except Exception as e:
        return jsonify({'error': str(e)[:200], 'frames': []}), 502


@app.route('/api/digitraffic/weather/<station_id>.json')
def api_digitraffic_weather(station_id):
    """Forward weather data for a station."""
    import urllib.request
    import socket
    socket.setdefaulttimeout(10)
    try:
        url = f'{DIGITRAFFIC_PROXY}/weather/{station_id}.json'
        req = urllib.request.Request(url, headers={'User-Agent': 'eli6-dashboard/1.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = r.read()
            return (data, 200, {
                'Content-Type': 'application/json',
                'Cache-Control': 'public, max-age=300',
                'Access-Control-Allow-Origin': '*',
            })
    except Exception as e:
        return jsonify({'error': str(e)[:200]}), 502


@app.route('/api/refresh')
def api_refresh():
    """Force re-read of CSV (slow — only call manually)."""
    global _CSV_MTIME, _DB_READY, _CAMS
    with _LOCK:
        _CSV_MTIME = 0
        _DB_READY = False
        _CAMS = []
    _ensure_db(force_reload=True)
    return jsonify({'ok': True, 'rows': len(_CAMS), 'mtime': _CSV_MTIME})


# ====== AI ENDPOINTS ======
@app.route('/api/ai/snapshot')
def api_ai_snapshot():
    """One-line natural-language summary of all cams."""
    _ensure_db()
    cur = _DB_CONN.cursor()
    cur.execute("SELECT COUNT(*) FROM cams WHERE live_status = 'live'")
    live = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT country) FROM cams WHERE country != '' AND live_status = 'live'")
    countries = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT city) FROM cams WHERE city != '' AND live_status = 'live'")
    cities = cur.fetchone()[0]
    cur.execute("SELECT country, COUNT(*) AS n FROM cams WHERE live_status = 'live' GROUP BY country ORDER BY n DESC LIMIT 1")
    top_country = cur.fetchone()
    cur.execute("SELECT type, COUNT(*) AS n FROM cams WHERE live_status = 'live' GROUP BY type ORDER BY n DESC LIMIT 1")
    top_type = cur.fetchone()
    cur.execute("SELECT COUNT(*) FROM cams WHERE live_status = 'live' AND lat IS NOT NULL")
    with_geo = cur.fetchone()[0]
    summary = (
        f"{live:,} cams live across {countries} countries and {cities} cities. "
        f"Top country: {top_country[0]} ({top_country[1]:,}). "
        f"Most common type: {top_type[0]} ({top_type[1]:,}). "
        f"{with_geo:,} cams have geo coordinates."
    )
    return jsonify({'summary': summary})


@app.route('/api/ai/insights')
def api_ai_insights():
    """Generate natural-language insights from cam data + structured chart data."""
    _ensure_db()
    cur = _DB_CONN.cursor()
    insights = []

    # Insight 1: top countries
    cur.execute("""
        SELECT country, COUNT(*) AS n,
               SUM(CASE WHEN type='hls' THEN 1 ELSE 0 END) AS hls,
               SUM(CASE WHEN type='mjpeg' THEN 1 ELSE 0 END) AS mjpeg,
               SUM(CASE WHEN type='youtube' THEN 1 ELSE 0 END) AS yt
        FROM cams WHERE live_status = 'live' AND country != ''
        GROUP BY country HAVING n >= 100
        ORDER BY n DESC LIMIT 8
    """)
    top_countries = []
    for r in cur.fetchall():
        country, n, hls, mjpeg, yt = r
        dom = 'HLS' if hls > mjpeg and hls > yt else 'MJPEG' if mjpeg > yt else 'YouTube'
        insights.append(f"📍 {country}: {n:,} cams. Dominant format: {dom} ({hls:,} HLS, {mjpeg:,} MJPEG, {yt:,} YT).")
        top_countries.append({'country': country, 'count': n, 'hls': hls or 0, 'mjpeg': mjpeg or 0, 'youtube': yt or 0})

    # Insight 2: ISP analysis
    cur.execute("""
        SELECT isp, COUNT(*) AS n FROM cams WHERE isp != ''
        GROUP BY isp HAVING n >= 50 ORDER BY n DESC LIMIT 6
    """)
    isps = cur.fetchall()
    if isps:
        isp_str = ', '.join(f'{n} {isp[:30]}' for isp, n in isps[:5])
        insights.append(f"🌐 Most cams hosted by: {isp_str}.")

    # Insight 3: type breakdown
    cur.execute("SELECT type, COUNT(*) AS n FROM cams WHERE type != '' AND live_status = 'live' GROUP BY type")
    type_counts = dict(cur.fetchall())
    type_chart = []
    if type_counts:
        total = sum(type_counts.values())
        breakdown = ', '.join(f'{int(v/total*100)}% {k}' for k, v in sorted(type_counts.items(), key=lambda x: -x[1]))
        insights.append(f"📊 Stream types: {breakdown}.")
        for k, v in sorted(type_counts.items(), key=lambda x: -x[1]):
            type_chart.append({'type': k, 'count': v, 'pct': round(v / total * 100, 1)})

    # Insight 4: random interesting find
    cur.execute("SELECT idx, name, country, city FROM cams WHERE name LIKE '%Beach%' AND live_status = 'live' LIMIT 1")
    r = cur.fetchone()
    if not r:
        cur.execute("SELECT idx, name, country, city FROM cams WHERE category = 'scenic' AND live_status = 'live' ORDER BY RANDOM() LIMIT 1")
        r = cur.fetchone()
    if r:
        insights.append(f"🌅 Random scenic cam: #{r['idx']} — {r['name']} ({r['city'] or '?'}, {r['country']})")

    # Insight 5: largest cam cluster
    cur.execute("""
        SELECT city, country, COUNT(*) AS n FROM cams
        WHERE city != '' AND live_status = 'live'
        GROUP BY city, country ORDER BY n DESC LIMIT 1
    """)
    r = cur.fetchone()
    if r:
        insights.append(f"🏙️ Biggest cam cluster: {r['n']:,} cams in {r['city']}, {r['country']}.")

    # Top regions
    cur.execute("""
        SELECT region, country, COUNT(*) AS n FROM cams
        WHERE region != '' AND country != '' AND live_status = 'live'
        GROUP BY region, country ORDER BY n DESC LIMIT 10
    """)
    top_regions = [{'region': r['region'], 'country': r['country'], 'count': r['n']} for r in cur.fetchall()]

    return jsonify({
        'insights': insights,
        'top_countries': top_countries,
        'top_regions': top_regions,
        'type_breakdown': type_chart,
    })


@app.route('/api/ai/hotspots')
def api_ai_hotspots():
    """DBSCAN clustering on lat/lon — find cam hotspots."""
    _ensure_db()
    # Limit to 10k to keep CPU reasonable
    cur = _DB_CONN.cursor()
    cur.execute("SELECT idx, name, lat, lon, country, city, type FROM cams WHERE lat IS NOT NULL AND lon IS NOT NULL AND live_status = 'live' ORDER BY RANDOM() LIMIT 10000")
    pts = [(r['lat'], r['lon'], r['idx'], r['name'], r['country'], r['city'], r['type']) for r in cur.fetchall()]
    if len(pts) < 10:
        return jsonify({'clusters': [], 'noise': 0})
    # Simple DBSCAN
    try:
        from sklearn.cluster import DBSCAN
        import numpy as np
        coords = np.array([[p[0], p[1]] for p in pts])
        # ~3km eps for cams (cams near each other = cluster)
        # 1 degree ≈ 111km, so 0.03° ≈ 3km
        db = DBSCAN(eps=0.5, min_samples=3, metric='euclidean').fit(coords)
        labels = db.labels_
        clusters = {}
        for i, lbl in enumerate(labels):
            if lbl == -1:
                continue
            if lbl not in clusters:
                clusters[lbl] = {'count': 0, 'center_lat': 0, 'center_lon': 0, 'samples': [], 'countries': set(), 'cities': set()}
            c = clusters[lbl]
            c['count'] += 1
            c['center_lat'] += pts[i][0]
            c['center_lon'] += pts[i][1]
            if len(c['samples']) < 5:
                c['samples'].append({'idx': pts[i][2], 'name': pts[i][3], 'type': pts[i][6]})
            if pts[i][4]: c['countries'].add(pts[i][4])
            if pts[i][5]: c['cities'].add(pts[i][5])
        out = []
        for lbl, c in clusters.items():
            if c['count'] >= 3:
                out.append({
                    'cluster_id': int(lbl),
                    'count': c['count'],
                    'center': [c['center_lat']/c['count'], c['center_lon']/c['count']],
                    'samples': c['samples'],
                    'countries': list(c['countries']),
                    'cities': list(c['cities'])[:5],
                })
        out.sort(key=lambda x: -x['count'])
        return jsonify({'clusters': out[:50], 'total_pts': len(pts), 'noise': int((labels == -1).sum())})
    except ImportError:
        return jsonify({'clusters': [], 'note': 'sklearn not available'})


@app.route('/api/ai/similar/<int:idx>')
def api_ai_similar(idx):
    """Find cams similar to <idx>."""
    _ensure_db()
    cur = _DB_CONN.cursor()
    cur.execute('SELECT * FROM cams WHERE idx = ?', (idx,))
    src = cur.fetchone()
    if not src:
        abort(404)
    src_country = src['country']
    src_city = src['city']
    src_isp = src['isp']
    src_type = src['type']
    src_cat = src['category']

    # Score-based similarity
    cur.execute("""
        SELECT * FROM (
          SELECT idx, name, type, country, city, category, isp, lat, lon,
                 (CASE WHEN country = ? THEN 10 ELSE 0 END) +
                 (CASE WHEN city = ? AND city != '' THEN 20 ELSE 0 END) +
                 (CASE WHEN isp = ? AND isp != '' THEN 5 ELSE 0 END) +
                 (CASE WHEN type = ? AND type != '' THEN 3 ELSE 0 END) +
                 (CASE WHEN category = ? AND category != '' THEN 4 ELSE 0 END) AS score
          FROM cams WHERE idx != ? AND live_status = 'live'
        ) WHERE score > 0 ORDER BY score DESC, idx ASC LIMIT 24
    """, (src_country, src_city, src_isp, src_type, src_cat, idx))
    similar = []
    for r in cur.fetchall():
        similar.append({
            'idx': r['idx'], 'name': r['name'], 'type': r['type'],
            'country': r['country'], 'city': r['city'], 'category': r['category'],
            'isp': r['isp'], 'lat': r['lat'], 'lon': r['lon'],
            'score': r['score'],
        })
    return jsonify({'source': idx, 'similar': similar})


@app.route('/api/ai/search')
def api_ai_search():
    """AI-powered smart search with intent detection."""
    _ensure_db()
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify({'intent': 'empty', 'results': [], 'explanation': 'empty query'})

    q_lower = q.lower()
    intent = 'keyword'
    explanation = ''
    extras = {}

    # Detect intent
    if re.match(r'^-?\d+(\.\d+)?\s*[, ]\s*-?\d+(\.\d+)?$', q):
        intent = 'coords'
        lat, lon = map(float, re.split(r'[, ]+', q))
        bbox = 5
        extras = {'lat': lat, 'lon': lon, 'radius_deg': bbox}
        explanation = f"Looking for cams within {bbox}° of ({lat}, {lon})"
    elif re.match(r'^https?://', q):
        intent = 'url_pattern'
        m = re.search(r'://(?:www\.)?([^/]+)', q)
        domain = m.group(1) if m else ''
        extras = {'domain': domain, 'url': q}
        explanation = f"Looking for cams on host '{domain}'"
    elif re.match(r'^\d{1,3}(\.\d{1,3}){0,3}$', q.replace(' ', '')):
        intent = 'ip'
        ip = q.replace(' ', '')
        extras = {'ip': ip}
        explanation = f"Looking for cams referencing IP {ip}"
    elif 'near' in q_lower or 'around' in q_lower:
        intent = 'near'
        m = re.search(r'(-?\d+\.?\d*)[, ]+(-?\d+\.?\d*)', q)
        if m:
            lat, lon = float(m.group(1)), float(m.group(2))
            bbox = 3
            extras = {'lat': lat, 'lon': lon, 'radius_deg': bbox}
            explanation = f"Looking for cams within {bbox}° of ({lat}, {lon})"
    elif q_lower in ('hls', 'mjpeg', 'youtube', 'mp4'):
        intent = 'type'
        type_map = {'hls': 'hls', 'mjpeg': 'mjpeg', 'youtube': 'youtube', 'mp4': 'mp4'}
        extras = {'type': type_map[q_lower]}
        explanation = f"Looking for all {q_lower.upper()} cams"
    elif q_lower.startswith('cat:'):
        intent = 'category'
        extras = {'category': q[4:].strip()}
        explanation = f"Looking for cams in category '{q[4:].strip()}'"
    elif q_lower.startswith('isp:'):
        intent = 'isp'
        extras = {'isp': q[4:].strip()}
        explanation = f"Looking for cams hosted by '{q[4:].strip()}'"
    else:
        intent = 'keyword'
        explanation = f"Searching cam names, cities, and metadata for '{q}'"

    # Build redirect to /api/cams
    params = {'limit': 200}
    if intent == 'coords' or intent == 'near':
        # Use geo bbox — adjust cam endpoint to support this
        params['country'] = ''
        cur = _DB_CONN.cursor()
        cur.execute("SELECT idx, name, type, country, city, lat, lon FROM cams WHERE lat BETWEEN ? AND ? AND lon BETWEEN ? AND ? AND live_status = 'live' ORDER BY idx LIMIT ?",
                    (extras['lat']-extras['radius_deg'], extras['lat']+extras['radius_deg'],
                     extras['lon']-extras['radius_deg'], extras['lon']+extras['radius_deg'],
                     params['limit']))
        results = []
        for r in cur.fetchall():
            dist = ((r['lat']-extras['lat'])**2 + (r['lon']-extras['lon'])**2)**0.5
            results.append({**{k: r[k] for k in r.keys()}, 'distance_deg': dist})
        results.sort(key=lambda x: x['distance_deg'])
        return jsonify({'intent': intent, 'results': results[:50], 'explanation': explanation, 'count': len(results)})

    if intent == 'type':
        params['type'] = extras['type']
    elif intent == 'category':
        params['q'] = extras['category']
    elif intent == 'isp':
        params['q'] = extras['isp']
    elif intent == 'url_pattern':
        params['q'] = extras['domain']
    elif intent == 'ip':
        params['q'] = extras['ip']
    else:
        params['q'] = q

    # Call internal cams endpoint logic
    with app.test_request_context(f'/api/cams?{request.query_string.decode()}'):
        resp = api_cams()
    data = resp.get_json()
    return jsonify({
        'intent': intent,
        'explanation': explanation,
        'count': data.get('count', 0),
        'results': data.get('cams', []),
    })


@app.route('/api/ai/query', methods=['GET', 'POST'])
def api_ai_query():
    """AI chat — answer natural-language questions about the cam database."""
    _ensure_db()
    if request.method == 'POST':
        body = request.get_json(silent=True) or {}
        q = (body.get('q') or '').strip()
    else:
        q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify({'answer': 'Please ask a question.', 'results': []})

    import re as _re
    q_lower = q.lower()
    cur = _DB_CONN.cursor()
    answer = ''
    sql_results = []

    # 1. "top N countries/cities/ISPs by cams" - optionally in COUNTRY
    m_top = _re.search(r'top\s+(\d+)?\s*(countries|cities|isps|regions|brands|categories)(?:\s+in\s+([A-Za-z\s]+?))?(?:\s*\?|$|\s*\.)', q, _re.IGNORECASE)
    if m_top:
        n = int(m_top.group(1) or 5)
        n = min(50, max(1, n))
        col = m_top.group(2).lower()
        country_filter = (m_top.group(3) or '').strip()
        col_map = {
            'countries': 'country', 'cities': 'city', 'isps': 'isp',
            'regions': 'region', 'brands': 'brand', 'categories': 'category',
        }
        c = col_map[col]
        if country_filter and len(country_filter) < 60:
            rows = cur.execute(f"SELECT {c} AS name, COUNT(*) AS n FROM cams WHERE live_status='live' AND {c} != '' AND country LIKE ? GROUP BY {c} ORDER BY n DESC LIMIT ?", (f'%{country_filter}%', n)).fetchall()
            answer = f"Top {n} {col} in '{country_filter}' by live cam count:\n" + '\n'.join(f"  {i+1}. {r['name']}: {r['n']:,}" for i, r in enumerate(rows))
        else:
            rows = cur.execute(f"SELECT {c} AS name, COUNT(*) AS n FROM cams WHERE live_status='live' AND {c} != '' GROUP BY {c} ORDER BY n DESC LIMIT ?", (n,)).fetchall()
            answer = f"Top {n} {col} by live cam count:\n" + '\n'.join(f"  {i+1}. {r['name']}: {r['n']:,}" for i, r in enumerate(rows))
        sql_results = [dict(r) for r in rows]
        return jsonify({'answer': answer, 'results': sql_results, 'type': 'top'})

    # 2. "cams in COUNTRY" (or city) - optional "by TYPE"
    m_in = _re.search(r'cams?\s+in\s+([A-Za-z\s,]+?)(?:\s+by\s+(\w+))?(?:\s*\?|$|\s*\.)', q, _re.IGNORECASE)
    if m_in:
        place = m_in.group(1).strip().rstrip('.,')
        type_filter = (m_in.group(2) or '').lower()
        if place and len(place) < 60:
            # Try country first, then city
            where_parts = ["live_status='live'"]
            params = []
            if type_filter and type_filter in ('hls', 'mjpeg', 'youtube', 'mp4'):
                where_parts.append("type = ?")
                params.append(type_filter)
            # Country match
            where_parts.append("(country LIKE ? OR city LIKE ? OR region LIKE ?)")
            params.extend([f'%{place}%'] * 3)
            where_sql = 'WHERE ' + ' AND '.join(where_parts)
            rows = cur.execute(f"SELECT name, city, country, type, lat, lon, idx FROM cams {where_sql} ORDER BY idx LIMIT 30", params).fetchall()
            cnt = cur.execute(f"SELECT COUNT(*) FROM cams {where_sql}", params).fetchone()[0]
            if cnt > 0:
                # type breakdown
                type_rows = cur.execute(f"SELECT type, COUNT(*) AS n FROM cams {where_sql} GROUP BY type ORDER BY n DESC", params).fetchall()
                breakdown = ', '.join(f"{r['n']:,} {r['type'].upper()}" for r in type_rows)
                answer = f"Found {cnt:,} live cams matching '{place}'{f' (type={type_filter})' if type_filter else ''}.\nType breakdown: {breakdown}.\nShowing first 30:"
                answer += '\n' + '\n'.join(f"  - {r['name']} ({r['city'] or '?'}, {r['country']}) [{r['type'].upper()}]" for r in rows)
                sql_results = [dict(r) for r in rows]
                return jsonify({'answer': answer, 'results': sql_results, 'type': 'place_lookup'})
            else:
                # Try alternate place names
                if place.upper() in ('NYC', 'NY', 'LA', 'SF', 'DC', 'UK'):
                    aliases = {'NYC': 'New York', 'NY': 'United States', 'LA': 'United States', 'SF': 'United States', 'DC': 'United States', 'UK': 'United Kingdom'}
                    alt = aliases.get(place.upper())
                    if alt:
                        params_alt = [alt, alt, alt]
                        if type_filter in ('hls', 'mjpeg', 'youtube', 'mp4'):
                            rows = cur.execute(f"SELECT name, city, country, type, lat, lon, idx FROM cams {where_sql} ORDER BY idx LIMIT 30", params[:1] + params_alt).fetchall()
                            cnt = cur.execute(f"SELECT COUNT(*) FROM cams {where_sql}", params[:1] + params_alt).fetchone()[0]
                            if cnt > 0:
                                answer = f"Found {cnt:,} live cams in '{alt}' (alias for '{place}'). Showing first 30."
                                sql_results = [dict(r) for r in rows]
                                return jsonify({'answer': answer, 'results': sql_results, 'type': 'place_lookup'})

    # 3. "type breakdown" or "how many hls cams"
    m_type = _re.search(r'(?:how many|count|number of|breakdown of)?\s*(hls|mjpeg|youtube|mp4)\s*(cams|streams)', q_lower)
    if m_type:
        t = m_type.group(1)
        cnt = cur.execute("SELECT COUNT(*) FROM cams WHERE live_status='live' AND type = ?", (t,)).fetchone()[0]
        answer = f"{cnt:,} live {t.upper()} cams in the database."
        sql_results = [{'type': t, 'count': cnt}]
        return jsonify({'answer': answer, 'results': sql_results, 'type': 'type_count'})

    # 4. "category X" / "traffic cams"
    for cat in ['traffic', 'weather', 'beach', 'mountain', 'city', 'public', 'port', 'harbor', 'lake', 'river', 'ski', 'scenic', 'rail', 'animal-care', 'water']:
        if cat in q_lower:
            cnt = cur.execute("SELECT COUNT(*) FROM cams WHERE live_status='live' AND category = ?", (cat,)).fetchone()[0]
            rows = cur.execute("SELECT name, country, city, type, idx FROM cams WHERE live_status='live' AND category = ? ORDER BY confidence DESC LIMIT 15", (cat,)).fetchall()
            answer = f"{cnt:,} live cams in category '{cat}'. Top examples:\n" + '\n'.join(f"  - {r['name']} ({r['city']}, {r['country']}) [{r['type'].upper()}]" for r in rows)
            sql_results = [dict(r) for r in rows]
            return jsonify({'answer': answer, 'results': sql_results, 'type': 'category'})

    # 5. Fallback: keyword search via FTS
    fts_q = ' '.join(c for c in _re.split(r'\W+', q) if c and c.lower() not in ('how', 'many', 'show', 'me', 'what', 'is', 'are', 'the', 'a', 'an', 'in', 'on', 'at', 'by'))
    if fts_q:
        fts_q = ' '.join(w + '*' for w in fts_q.split()[:6])
        try:
            rows = cur.execute("SELECT name, country, city, type, idx FROM cams WHERE idx IN (SELECT idx FROM cams_fts WHERE cams_fts MATCH ?) AND live_status='live' LIMIT 20", (fts_q,)).fetchall()
            if rows:
                cnt = cur.execute("SELECT COUNT(*) FROM cams WHERE idx IN (SELECT idx FROM cams_fts WHERE cams_fts MATCH ?) AND live_status='live'", (fts_q,)).fetchone()[0]
                answer = f"Matched {cnt:,} cams for '{q}'. Top results:\n" + '\n'.join(f"  - {r['name']} ({r['city']}, {r['country']})" for r in rows)
                sql_results = [dict(r) for r in rows]
                return jsonify({'answer': answer, 'results': sql_results, 'type': 'fts'})
        except Exception:
            pass

    answer = f"Sorry, I couldn't interpret '{q}'. Try: 'top 5 countries', 'cams in Japan', 'traffic cams', or '500 hls cams'."
    return jsonify({'answer': answer, 'results': [], 'type': 'unknown'})


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print(f'[eli6-d] starting on 127.0.0.1:{port}')
    _ensure_db()
    app.run(host='127.0.0.1', port=port, threaded=True, debug=False)