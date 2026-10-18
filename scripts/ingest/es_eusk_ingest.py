# -*- coding: utf-8 -*-
"""Session 47h - Euskadi open-data harvest ingest (3 phases, one atomic write).

Phase A (gip): 8 Gipuzkoa coastal webcam HLS streams (Diputación Foral de
    Gipuzkoa beach pages + zumaia.eus), streamlock.net/camaramar family.
    3 sibling streams already ingested as tv_121095/96/108.
Phase B (blb): 24 new Bilbao Ayto codec cameras from
    bilbao.eus srvDatasetCamaras geojson (wayback snapshot 20240509).
    www.bilbao.eus = 403 WAF for our IP (curl + browser) -> live_status=''.
Phase C (fix): rectify junk aggregator titles on already-correct rows:
    - trafikoa disc rows named "... · Apps · #N" -> official GV title
    - bizkaimove disc rows named "... · Bizkaimove · #N" -> official DFB name
    Only project_name + notes change (coords proven correct already).

Inputs: %TEMP%\\gv_cams.geojson, %TEMP%\\dfb_en.csv, %TEMP%\\ab_wayback.geojson
"""
import csv
import html
import io
import json
import os
import re
import subprocess
import tempfile
import unicodedata

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
CSV = os.path.join(ROOT, "controllable_Webcams.csv")
STATE = os.path.join(ROOT, "camera_testing", "es_eusk_ingest_state.json")
LOCK = CSV + ".lock"
T = os.environ.get("TEMP", r"C:\Windows\Temp")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
REGION = "Euskadi"

GIP_STREAMS = [
    # slug, stream, project_name, city, zip, lat, lon, page_title_extra
    ("ondarreta", "GIP_ondarreta_169", "Playa de Ondarreta (Ondarreta Beach)",
     "Donostia / San Sebastian", "20018", 43.31840, -1.99220, "Webcam en directo de la playa de Ondarreta (Diputacion Foral de Gipuzkoa)"),
    ("orio", "GIP_orio_169", "Playa de Orio (Orio Beach)",
     "Orio", "20115", 43.18800, -2.12750, "Webcam en directo de la playa de Orio (Diputacion Foral de Gipuzkoa)"),
    ("zarautz", "GIP_zarautz_169", "Playa de Zarautz (Zarautz Beach)",
     "Zarautz", "20800", 43.31070, -2.17440, "Webcam en directo de la playa de Zarautz (Diputacion Foral de Gipuzkoa)"),
    ("malkorbe", "GIP_getaria_169", "Playa de Malkorbe, Getaria (Malkorbe Beach)",
     "Getaria", "20808", 43.30550, -2.19900, "Webcam en directo de la playa de Malkorbe (Diputacion Foral de Gipuzkoa)"),
    ("deba", "GIP_deba_169", "Playa de Deba (Deba Beach)",
     "Deba", "20820", 43.29580, -2.35470, "Webcam en directo de la playa de Deba (Diputacion Foral de Gipuzkoa)"),
    ("puerto-mutriku", "GIP_mutrikukaia_169", "Webcam Puerto de Mutriku (Mutriku Harbour)",
     "Mutriku", "20830", 43.13600, -2.38450, "Webcam en directo del puerto de Mutriku (Diputacion Foral de Gipuzkoa)"),
    ("saturraran", "GIP_saturraran_169", "Playa de Saturraran, Mutriku (Saturraran Beach)",
     "Mutriku", "20830", 43.27780, -2.38880, "Webcam en directo de la playa de Saturraran (Diputacion Foral de Gipuzkoa)"),
    ("zumaia", "GIP_zumaia2", "Webcam Zumaia (Zumaia Beach)",
     "Zumaia", "20750", 43.27900, -2.26180, "Webcam - Turismo Zumaia"),
]
GIP_PAGE = "https://www.gipuzkoa.eus/es/web/hondartzak/webcams/{slug}"
ZUMAIA_PAGE = "http://zumaia.eus/es/turismo/que-hacer/webcam"
BLB_ORG = "Ayuntamiento de Bilbao"
GIP_ORG = "Diputacion Foral de Gipuzkoa"


def curl_meta(url, timeout=25):
    fd, tmp = tempfile.mkstemp(suffix=".bin")
    os.close(fd)
    try:
        p = subprocess.run(
            ["curl", "-s", "-A", UA, "--max-time", str(timeout), "-o", tmp,
             "-w", "%{http_code}|%{content_type}", url],
            capture_output=True, text=True, timeout=timeout + 10,
        )
        meta = (p.stdout or "").strip().split("|")
        code = int(meta[0]) if meta and meta[0].isdigit() else 0
        ctype = meta[1] if len(meta) > 1 else ""
        return code, (ctype or "").split(";")[0].strip()
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def norm(s):
    s = html.unescape(s or "")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9]+", " ", s).upper().strip()
    return s


def cam_id(url):
    m = re.search(r"camaras/(\d+)\s*\.jpg", url or "", re.I)
    if m:
        return "trk" + m.group(1)
    m = re.search(r"/cam(\d+)\.jpg", url or "", re.I)
    if m:
        return "bm" + m.group(1)
    m = re.search(r"codec(\d+)", url or "", re.I)
    if m:
        return "blb" + m.group(1)
    m = re.search(r"CamarasMunicipales/(\d+)", url or "", re.I)
    if m:
        return "geo" + m.group(1)
    return None


def better_name(a, b):
    """Prefer human text (has lowercase word) over raw ALL-CAPS codes."""
    def human(s):
        return 1 if re.search(r"[a-z]{3}", s or "") else 0
    return a if human(a) >= human(b) else b


def main():
    if os.path.exists(LOCK):
        raise SystemExit("lock exists: " + LOCK)
    lock_fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(lock_fd)
    try:
        state = {}
        if os.path.exists(STATE):
            state = json.load(open(STATE, encoding="utf-8"))
        if state.get("rows_after") and state.get("phase") == "done":
            raise SystemExit("state=done already (delete state file to rerun)")

        with open(CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)
        base_count = len(rows)

        # ---------- catalogs ----------
        gv = json.loads(open(os.path.join(T, "gv_cams.geojson"), encoding="utf-8", errors="replace")
                        .read().split("jsonCallback(", 1)[1].rsplit(")", 1)[0])
        cat_trk = {}
        for f_ in gv["features"]:
            p = f_["properties"]
            k = cam_id(p.get("url cam"))
            if k:
                cat_trk[k] = {"title": p.get("title") or "", "road": p.get("road"), "pk": p.get("pk")}

        dfb_raw = open(os.path.join(T, "dfb_en.csv"), encoding="utf-8-sig", errors="replace").read()
        cat_bm = {}
        for r_ in csv.DictReader(io.StringIO(dfb_raw)):
            u = (r_.get("URL") or "").strip()
            k = cam_id(u)
            if not k:
                continue
            nm = r_.get("IZENA/NOMBRE") or ""
            prev = cat_bm.get(k)
            if prev is None:
                cat_bm[k] = {"name": nm, "road": r_.get("ERREPIDEA/CARRETERA"), "pk": r_.get("PK")}
            else:
                merged = dict(prev)
                merged["name"] = better_name(prev["name"], nm)
                if not merged.get("road"):
                    merged["road"] = r_.get("ERREPIDEA/CARRETERA")
                if not merged.get("pk"):
                    merged["pk"] = r_.get("PK")
                cat_bm[k] = merged

        ab = json.load(open(os.path.join(T, "ab_wayback.geojson"), encoding="utf-8"))

        # ---------- overlap guards ----------
        existing_blb = [r_["csv_id"] for r_ in rows if "camarastrafico/codec" in ((r_.get("live_stream_url") or "") + (r_.get("url") or ""))]
        assert not existing_blb, f"codec rows already exist: {existing_blb[:5]}"

        next_idx = max(int(r_["idx"]) for r_ in rows) + 1
        new_rows = []
        results = []

        # ---------- Phase A: Gipuzkoa HLS streams ----------
        gip_done = state.get("phase_a") == "done"
        if not gip_done:
            for slug, stream, name, city, zc, lat, lon, desc in GIP_STREAMS:
                m3u8 = f"https://58f14c0895a20.streamlock.net/camaramar/{stream}.stream/playlist.m3u8"
                assert m3u8.lower() not in {( (r_.get("live_stream_url") or "").lower()) for r_ in rows}, m3u8
                page = ZUMAIA_PAGE if slug == "zumaia" else GIP_PAGE.format(slug=slug)
                code, ctype = curl_meta(m3u8, 20)
                live = code == 200 and "mpegurl" in (ctype or "").lower()
                notes = [
                    f"stream={stream}",
                    "src=gipuzkoa.eus:playas-webcams" if slug != "zumaia" else "src=zumaia.eus:webcam",
                    "feedType=video",
                    "lm=2026-10-18",
                    f"probe={code}@2026-10-18",
                ]
                if not live:
                    notes.append("stream-404@2026-10-18" if code == 404 else f"probe-failed-{code}@2026-10-18")
                idx = next_idx
                row = {k: "" for k in fieldnames}
                row.update({
                    "idx": str(idx),
                    "csv_id": f"gip_{idx:04d}",
                    "project_name": name,
                    "url": page,
                    "live_stream_url": m3u8,
                    "type": "video",
                    "enabled": "True",
                    "live_status": "live" if live else "",
                    "http_status": str(code) if code else "",
                    "content_type": ctype,
                    "description": desc,
                    "category": "scenic",
                    "likely_subject": "Beach webcam live video (Gipuzkoa)",
                    "country": "Spain",
                    "region": REGION,
                    "city": city,
                    "zip": zc,
                    "lat": f"{lat:.6f}",
                    "lon": f"{lon:.6f}",
                    "location_precision": "",
                    "geo_source": "manual:beach-centroid",
                    "org": GIP_ORG,
                    "host": "58f14c0895a20.streamlock.net",
                    "confidence": "high",
                    "notes": "; ".join(notes),
                    "visibility": "",
                })
                new_rows.append(row)
                results.append((row["csv_id"], name, live, code))
                next_idx += 1

        # ---------- Phase B: Bilbao codec cams ----------
        blb_done = state.get("phase_b") == "done"
        blb_added = []
        if not blb_done:
            geo_names = set(norm(r_.get("project_name") or "") for r_ in rows
                            if cam_id((r_.get("live_stream_url") or "") + " " + (r_.get("url") or "")) is not None
                            and cam_id((r_.get("live_stream_url") or "") + " " + (r_.get("url") or ""))[:3] == "geo")
            if not geo_names:
                geo_names = set(norm(r_.get("project_name") or "") for r_ in rows
                                if "geobilbao" in ((r_.get("live_stream_url") or "") + (r_.get("url") or "")))
            unmatched = []
            for f_ in ab["features"]:
                p_ = f_["properties"]
                k = cam_id(p_.get("URL", ""))
                n = norm(p_.get("Nombre") or "")
                hit = n in geo_names
                if not hit:
                    for gn in geo_names:
                        if n and (n in gn or gn in n):
                            hit = True
                            break
                if not hit:
                    xy = (f_.get("geometry") or {}).get("coordinates") or [None, None]
                    unmatched.append({"k": k, "props": p_, "lat": xy[1], "lon": xy[0]})
            assert len(unmatched) == 24, f"expected 24 new bilbao, got {len(unmatched)}"
            for e in sorted(unmatched, key=lambda x: x["k"]):
                name = html.unescape(e["props"].get("Nombre") or "").strip()
                url = e["props"].get("URL")
                idx = next_idx
                row = {k: "" for k in fieldnames}
                row.update({
                    "idx": str(idx),
                    "csv_id": f"blb_{idx:04d}",
                    "project_name": name,
                    "url": url,
                    "live_stream_url": url,
                    "type": "image",
                    "enabled": "True",
                    "live_status": "",
                    "http_status": "403",
                    "content_type": "text/html",
                    "description": e["props"].get("Texto_SPA") or name,
                    "category": "traffic",
                    "likely_subject": "Municipal traffic camera view (Bilbao Ayto)",
                    "country": "Spain",
                    "region": REGION,
                    "city": "Bilbao",
                    "lat": f'{e["lat"]:.7f}'.rstrip("0").rstrip("."),
                    "lon": f'{e["lon"]:.7f}'.rstrip("0").rstrip("."),
                    "location_precision": "precise",
                    "geo_source": "src:bilbao.eus-camaras",
                    "org": BLB_ORG,
                    "host": "www.bilbao.eus",
                    "confidence": "high",
                    "notes": "; ".join([
                        f"bilbao-codec-id={e['props'].get('Camid') or (e['k'] or '')[3:]}",
                        f"tipo={e['props'].get('Tipo') or 'Ayto'}",
                        "src=bilbao.eus:srvDatasetCamaras (wayback@20240509)",
                        "waf-403@2026-10-18",
                        "lm=2026-10-18",
                    ]),
                    "visibility": "",
                })
                new_rows.append(row)
                blb_added.append((row["csv_id"], name))
                next_idx += 1

        # ---------- Phase C: junk title rectification ----------
        fix_done = state.get("phase_c") == "done"
        fixed_trk, fixed_bm, skip_trk, skip_bm = 0, 0, 0, 0
        if not fix_done:
            for r_ in rows:
                u = (r_.get("live_stream_url") or "") + " " + (r_.get("url") or "")
                ul = u.lower()
                nm = r_.get("project_name") or ""
                if "trafikoa" in ul and "Apps" in nm and re.search(r"#\d+", nm):
                    k = cam_id(u)
                    cat = cat_trk.get(k)
                    if not cat:
                        skip_trk += 1
                        continue
                    new_nm = cat["title"]
                    if cat.get("road") and cat.get("pk") not in (None, ""):
                        new_nm = f'{cat["title"]} ({cat["road"]} pk{cat["pk"]})'
                    if new_nm and new_nm != nm:
                        r_["project_name"] = new_nm
                        notes = r_.get("notes") or ""
                        if "name-fixed=euskadi-ods@2026-10-18" not in notes:
                            r_["notes"] = (notes + "; " if notes else "") + "name-fixed=euskadi-ods@2026-10-18"
                        fixed_trk += 1
                elif "bizkaimove" in ul and re.search(r"(?i)[·�]\s*Bizkaimove\s*[·�]\s*#\d+", nm):
                    k = cam_id(u)
                    cat = cat_bm.get(k)
                    if not cat:
                        skip_bm += 1
                        continue
                    new_nm = cat["name"]
                    if cat.get("road") and cat.get("pk") not in (None, ""):
                        new_nm = f'{cat["name"]} ({cat["road"]} pk{cat["pk"]})'
                    if new_nm and new_nm != nm:
                        r_["project_name"] = new_nm
                        notes = r_.get("notes") or ""
                        if "name-fixed=euskadi-ods@2026-10-18" not in notes:
                            r_["notes"] = (notes + "; " if notes else "") + "name-fixed=euskadi-ods@2026-10-18"
                        fixed_bm += 1

        rows.extend(new_rows)
        tmp = CSV + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        os.replace(tmp, CSV)

        state.update({
            "date": "2026-10-18",
            "phase": "done",
            "gip_ingested": len(GIP_STREAMS) if not gip_done else state.get("gip_ingested"),
            "gip_live": sum(1 for _, _, l, _ in results if l) if results else state.get("gip_live"),
            "gip_dead": [c for c, _, l, _ in results if not l] if results else state.get("gip_dead"),
            "blb_ingested": len(blb_added) if not blb_done else state.get("blb_ingested"),
            "blb_ids": [c for c, _ in blb_added] if blb_added else state.get("blb_ids"),
            "fixed_trafikoa": fixed_trk if not fix_done else state.get("fixed_trafikoa"),
            "fixed_bizkaimove": fixed_bm if not fix_done else state.get("fixed_bizkaimove"),
            "skipped_no_catalog": {"trafikoa": skip_trk, "bizkaimove": skip_bm} if not fix_done else state.get("skipped_no_catalog"),
            "rows_before": base_count,
            "rows_after": len(rows),
            "idx_range": [next_idx - len(new_rows), next_idx - 1] if new_rows else None,
        })
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=1)

        print(f"[eusk] rows {base_count} -> {len(rows)} (+{len(new_rows)})")
        print(f"[gip] {len(GIP_STREAMS) if not gip_done else 0} streams, live={state.get('gip_live')}, dead={state.get('gip_dead')}")
        for c, n, l, code in results:
            print(f"  {c} {'live' if l else 'DEAD(%s)' % code} {n}")
        print(f"[blb] {len(blb_added) if not blb_done else 0} codec cams added: {[c for c, _ in blb_added]}")
        print(f"[fix] trafikoa={fixed_trk} (skip {skip_trk}) | bizkaimove={fixed_bm} (skip {skip_bm})")
    finally:
        try:
            os.remove(LOCK)
        except OSError:
            pass


if __name__ == "__main__":
    main()
