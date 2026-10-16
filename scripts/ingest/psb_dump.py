"""Full-detail dump of every PSB.li broadcast (14 expected).

Sources per id:
  1. search API sweep union (id/title/description/tags)  - enumeration
  2. GET /streaming/<id>                                 - HLS master URL
  3. GET /watch/<id>  (raw HTML saved)                   - ld+json, map/weather JS
  4. GET /thumb/<id>  (bytes saved)                      - camera overlay header + EXIF GPS
  5. GET master.m3u8 (+ first variant)                   - liveness, variants, bandwidth
Output: camera_testing/psb_dump.json + thumbnails in camera_testing/psb_thumbs/
"""
import json
import os
import re
import time
import urllib.request
import urllib.error

ROOT = r'C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing'
OUT = os.path.join(ROOT, 'psb_dump.json')
THUMBS = os.path.join(ROOT, 'psb_thumbs')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
HEX = '0123456789abcdef'


def get(url, timeout=20, binary=False):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
            return r.status, r.headers.get('Content-Type', ''), (data if binary else data.decode('utf-8', 'replace'))
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get('Content-Type', ''), ('' if binary else '')
    except Exception as e:
        return 0, type(e).__name__, ('' if binary else '')


def post_json(url, body, timeout=20):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={**UA, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode('utf-8', 'replace'))
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return 0, None


def enumerate_ids():
    """Union of 16 hex-char queries with pagination + sitemap."""
    ids = {}
    for ch in HEX:
        page = 1
        while page <= 50:
            st, d = post_json('https://www.psb.li/api/search?search=true', {'query': ch, 'page': page})
            res = (d or {}).get('results') or []
            for it in res:
                ids.setdefault(it['id'], it)
            if not res:
                break
            page += 1
            time.sleep(0.1)
    # sitemap
    st, _ct, sm = get('https://www.psb.li/sitemap_1.xml')
    for m in re.finditer(r'/watch/([0-9a-f]{12})', sm or ''):
        ids.setdefault(m.group(1), {'id': m.group(1), 'title': '', 'description': '', 'tags': []})
    return ids


def parse_thumb_header(blob):
    """Camera overlay text lines live at JPEG start (after FFD8...). Read first 400 bytes as latin-1."""
    head = blob[:400].decode('latin-1', 'replace')
    out = {}
    for key in ('DataLen', 'CamTim', 'FrmRate', 'TimStamp', 'CamPos', 'AlmEvent', 'AutoFlip'):
        m = re.search(key + r':\s*([^\r\n]+)', head)
        if m:
            out[key] = m.group(1).strip()
    return out


def parse_exif(blob):
    out = {}
    try:
        from PIL import Image
        from io import BytesIO
        im = Image.open(BytesIO(blob))
        ex = im.getexif()
        if ex:
            for tag_id in (0x010F, 0x0110, 0x0131, 0x8298, 0x9003):  # Make, Model, Software, Copyright, DateTimeOriginal
                v = ex.get(tag_id)
                if v:
                    out[f'exif_{tag_id:#x}'] = str(v)[:80]
            try:
                gps = ex.get_ifd(0x8825)
                if gps:
                    out['gps_raw'] = {str(k): str(v)[:60] for k, v in gps.items()}
            except Exception:
                pass
        out['size'] = f'{im.width}x{im.height}'
    except Exception as e:
        out['err'] = type(e).__name__
    return out


def probe_m3u8(url):
    st, ct, body = get(url)
    info = {'status': st, 'content_type': ct}
    if st != 200 or not body or '#EXTM3U' not in body:
        return info
    variants = []
    for m in re.finditer(r'#EXT-X-STREAM-INF:([^\n]+)\n([^\n]+)', body):
        attrs, uri = m.group(1), m.group(2).strip()
        bw = re.search(r'BANDWIDTH=(\d+)', attrs)
        res = re.search(r'RESOLUTION=(\d+x\d+)', attrs)
        variants.append({'bandwidth': int(bw.group(1)) if bw else None,
                         'resolution': res.group(1) if res else None,
                         'uri': uri})
    info['variants'] = variants
    info['is_master'] = bool(variants)
    if variants:
        vurl = variants[0]['uri']
        if not vurl.startswith('http'):
            vurl = url.rsplit('/', 1)[0] + '/' + vurl
        st2, ct2, body2 = get(vurl, timeout=15)
        info['variant1'] = {'url': vurl, 'status': st2,
                            'has_media': '#EXTINF' in (body2 or '') or '#EXT-X-TARGETDURATION' in (body2 or '')}
        if st2 == 200:
            seg = re.search(r'^(?!#)(\S+\.(?:ts|m4s|mp4)\S*)$', body2 or '', re.M)
            if seg:
                surl = seg.group(1).strip()
                if not surl.startswith('http'):
                    surl = vurl.rsplit('/', 1)[0] + '/' + surl
                st3, _, _ = get(surl, timeout=15)
                info['segment'] = {'status': st3}
    return info


def watch_extract(html, bid):
    out = {}
    m = re.search(r'(?s)<script type="application/ld\+json">(.*?)</script>', html)
    if m:
        try:
            g = json.loads(m.group(1)).get('@graph', [])
            for node in g:
                if node.get('@type') == 'VideoObject':
                    out['ld_name'] = node.get('name')
                    out['ld_description'] = node.get('description')
                    out['ld_thumbnail'] = node.get('thumbnailUrl')
                if node.get('@type') == 'BroadcastEvent':
                    out['ld_broadcast_name'] = node.get('name')
        except Exception:
            pass
    # topics/tags chips
    topics = re.findall(r'(?s)Topics and tags.{0,4000}?</section>', html)
    if topics:
        chips = re.findall(r'<(?:span|a|li)[^>]*class="[^"]*tag[^"]*"[^>]*>([^<]{1,60})<', topics[0])
        if chips:
            out['page_tags'] = [c.strip() for c in chips]
    # broadcast information table
    table = re.findall(r'(?s)Broadcast information(.{0,2500}?)</table>', html)
    if table:
        pairs = re.findall(r'<t[dh][^>]*>\s*([^<]{1,80}?)\s*</t[dh]>\s*<t[dh][^>]*>\s*([^<]{1,200}?)\s*</t[dh]>', table[0])
        if pairs:
            out['info_table'] = dict(pairs)
    # any lat/lon-ish floats in inline JS
    floats = re.findall(r'(-?\d{1,3}\.\d{4,})', html)
    if floats:
        out['float_literals'] = sorted(set(floats))[:12]
    # weather api call params
    wm = re.search(r'(?s)api/weather.{0,400}', html)
    if wm:
        out['weather_ctx'] = re.sub(r'\s+', ' ', wm.group(0))[:300]
    return out


def main():
    os.makedirs(THUMBS, exist_ok=True)
    ids = enumerate_ids()
    print(f'enumerated: {len(ids)} broadcasts', flush=True)
    dump = {}
    if os.path.exists(OUT):
        try:
            dump = json.load(open(OUT, encoding='utf-8'))
            for k, v in dump.items():
                cfg_status = (v.get('streaming') or {}).get('status')
                if 'watch_status' in v and v.get('thumb') and cfg_status != 0:
                    v['done'] = True
            print(f'resuming: {len(dump)} records already dumped', flush=True)
        except Exception:
            dump = {}
    for bid, meta in sorted(ids.items()):
        if dump.get(bid, {}).get('done'):
            continue
        rec = {
            'id': bid,
            'title': meta.get('title') or '',
            'description': meta.get('description') or '',
            'tags': meta.get('tags') or [],
            'watch_url': f'https://www.psb.li/watch/{bid}',
            'embed_url': f'https://www.psb.li/embed/{bid}',
            'thumb_url': f'https://www.psb.li/thumb/{bid}',
        }
        # streaming config
        st, _sct, body = get(f'https://www.psb.li/streaming/{bid}')
        try:
            cfg = json.loads(body)
            pc = (cfg.get('playerConfig') or [{}])[0]
            rec['streaming'] = {'status': st, 'main': pc.get('mainStreamUrl'),
                                'timelapse': pc.get('timelapseList') or [],
                                'playback_hls': pc.get('playbackHlsList') or []}
        except Exception:
            rec['streaming'] = {'status': st}
        # watch page
        st2, _, whtml = get(rec['watch_url'])
        rec['watch_status'] = st2
        if whtml:
            rec.update(watch_extract(whtml, bid))
            with open(os.path.join(ROOT, f'psb_watch_{bid}.html'), 'w', encoding='utf-8') as f:
                f.write(whtml)
        # thumbnail
        st3, ct3, tbytes = get(rec['thumb_url'], binary=True)
        rec['thumb'] = {'status': st3, 'content_type': ct3}
        if tbytes:
            rec['thumb'].update(parse_thumb_header(tbytes))
            rec['thumb'].update(parse_exif(tbytes))
            with open(os.path.join(THUMBS, f'{bid}.jpg'), 'wb') as f:
                f.write(tbytes)
        # stream probe
        murl = rec.get('streaming', {}).get('main')
        if murl:
            rec['stream_probe'] = probe_m3u8(murl)
        rec['done'] = True
        dump[bid] = rec
        with open(OUT, 'w', encoding='utf-8') as f:
            json.dump(dump, f, indent=2, ensure_ascii=False)
        print(f"  {bid} | {(rec['title'] or '(untitled)')[:38]:38} | stream={rec.get('streaming',{}).get('status')} "
              f"| m3u8={rec.get('stream_probe',{}).get('status')} "
              f"| campos={rec.get('thumb',{}).get('CamPos','-')}", flush=True)
        time.sleep(0.3)
    print(f'\nwrote {OUT} ({len(dump)} records)', flush=True)


if __name__ == '__main__':
    main()
