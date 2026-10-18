# -*- coding: utf-8 -*-
"""Session 47j - CRTVG (Tiivii tenant camarasweb.g24.gal) rectify.

All 30 CRTVG cams are already in the CSV as tv_100328..100357 +
tv_173000/173001 (TrafficVision, g24 family, public). No new rows.

Official source: https://camarasweb.g24.gal tenant config
/assets/camarasweb.g24.gal/config.json (Tiivii platform, generated
2026-10-18, 26 active cams with exact lat/lon + official names +
English descriptions + HLS urls on www.crtvg.es:1554-1556).

Fixes:
- 26 config cams: official name, exact coords (trafficvision geocoder
  was junk on several - Arua at 42.97/-8.5 = Santiago province, Bando
  city Rianxo, Mourense 42.17/-7.53), city from official description,
  zip cleared when city changes, description = official description_en,
  geo_source -> src:camarasweb.g24.gal + precise.
- Honest live re-probe of all 30 m3u8: 25 live / 5 x404 (catedral_nc,
  catedral_nl, ogrove, ortigueira retired from config; sanxenxo in
  config but stream 404) -> live_status='', http_status=404.
- notes += rectified marker.
Posters: skipped (video rows carry none - gip precedent).
"""
import csv
import json
import os
import subprocess
import tempfile

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
CSV = os.path.join(ROOT, "controllable_Webcams.csv")
STATE = os.path.join(ROOT, "camera_testing", "_crtvg_fix_state.json")
LOCK = CSV + ".lock"
T = os.environ.get("TEMP", r"C:\Windows\Temp")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
MARK = "rectified=crtvg-tiivii@2026-10-18"
GEO = "src:camarasweb.g24.gal"

# csv_id -> municipality (name comes verbatim from cfg c['name'])
NAMES_CITIES = {
    "tv_100328": "A Coru\u00f1a",
    "tv_100329": "A Coru\u00f1a",
    "tv_100330": "A Guarda",
    "tv_100331": "A R\u00faa",
    "tv_100332": "Baiona",
    "tv_100333": "Manzaneda",
    "tv_100334": "Fisterra",
    "tv_100337": "Celanova",
    "tv_100338": "Ares",
    "tv_100339": "Lal\u00edn",
    "tv_100340": "Lugo",
    "tv_100342": "Pedrafita do Cebreiro",
    "tv_100345": "Ourense",
    "tv_100346": "Ourense",
    "tv_100347": "Santiago de Compostela",
    "tv_100348": "Pontevedra",
    "tv_100349": "Portomar\u00edn",
    "tv_100350": "Portonovo",
    "tv_100351": "Santiago de Compostela",
    "tv_100352": "Santiago de Compostela",
    "tv_100353": "Santiago de Compostela",
    "tv_100354": "Santiago de Compostela",
    "tv_100355": "Sanxenxo",
    "tv_100356": "Tui",
    "tv_100357": "Ver\u00edn",
    "tv_173000": "Mux\u00eda",
    "tv_173001": "Ortigueira",
}
# tv_100335/100336 keep existing names (catedral views), tv_100343 keeps
# 'O Grove' - all dead, not in config: live_status only.

DEAD_ONLY = {"tv_100335", "tv_100336", "tv_100343"}


def probe(url, timeout=25):
    fd, tmp = tempfile.mkstemp(suffix=".bin")
    os.close(fd)
    try:
        p = subprocess.run(
            ["curl", "-sL", "-A", UA, "--max-time", str(timeout), "-o", tmp,
             "-w", "%{http_code}|%{content_type}|%{size_download}", url],
            capture_output=True, text=True, timeout=timeout + 10)
        meta = (p.stdout or "").strip().split("|")
        return (int(meta[0]) if meta and meta[0].isdigit() else 0,
                meta[1] if len(meta) > 1 else "",
                int(float(meta[2])) if len(meta) > 2 and meta[2] else 0)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def main():
    if os.path.exists(LOCK):
        raise SystemExit("lock exists: " + LOCK)
    lock_fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(lock_fd)
    try:
        if os.path.exists(STATE):
            st = json.load(open(STATE, encoding="utf-8"))
            if st.get("phase") == "done":
                raise SystemExit("already done (delete state to rerun)")
        cfg = json.load(open(os.path.join(T, "tiivii_cfg.json"), encoding="utf-8"))
        cfg_by_url = {c["url"]: c for c in cfg["cameras"]}
        assert len(cfg["cameras"]) == 26

        with open(CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)

        renamed = coords_fixed = dead = live_ok = 0
        touched = []
        for r in rows:
            u = (r.get("live_stream_url") or "") + " " + (r.get("url") or "")
            if "crtvg.es" not in u:
                continue
            cid = r["csv_id"]
            url = r["live_stream_url"] or r["url"]
            code, ctype, size = probe(url)
            notes = r.get("notes") or ""
            c = cfg_by_url.get(url)

            if code == 200 and "mpegurl" in (ctype or "").lower():
                r["live_status"] = "live"
                r["http_status"] = "200"
                r["content_type"] = "application/vnd.apple.mpegurl"
                live_ok += 1
            else:
                r["live_status"] = ""
                r["http_status"] = str(code) if code else ""
                r["content_type"] = ctype
                dead += 1
                if "hls-404@2026-10-18" not in notes:
                    extra = "hls-404@2026-10-18; "
                    extra += "not-in-tiivii-config@2026-10-18" if not c else "in-config-stream-down"
                    notes = (notes + "; " if notes else "") + extra

            if c:
                loc = c.get("location") or {}
                new_name = c["name"]
                new_city = NAMES_CITIES.get(cid, r["city"])
                if r["project_name"] != new_name:
                    r["project_name"] = new_name
                    renamed += 1
                if r["city"] != new_city:
                    r["city"] = new_city
                    r["zip"] = ""
                if str(r.get("lat") or "") != str(loc.get("lat")) or \
                        str(r.get("lon") or "") != str(loc.get("lon")):
                    coords_fixed += 1
                r["lat"] = str(loc.get("lat"))
                r["lon"] = str(loc.get("lon"))
                r["location_precision"] = "precise"
                r["geo_source"] = GEO
                r["description"] = c.get("description_en") or r.get("description") or ""
                r["region"] = "Galicia"
                if MARK not in notes:
                    notes = (notes + "; " if notes else "") + \
                        "tiivii-id=%s; %s" % (c["id"], MARK)

            if MARK not in notes:
                notes = (notes + "; " if notes else "") + MARK
            r["notes"] = notes
            touched.append(cid)

        assert len(touched) == 30, touched
        tmp = CSV + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        os.replace(tmp, CSV)

        state = {"date": "2026-10-18", "phase": "done", "touched": touched,
                 "renamed": renamed, "coords_fixed": coords_fixed,
                 "live": live_ok, "dead": dead, "rows_after": len(rows)}
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=1)
        print("[crtvg] touched=%d renamed=%d coords_fixed=%d live=%d dead=%d total=%d" % (
            len(touched), renamed, coords_fixed, live_ok, dead, len(rows)))
    finally:
        try:
            os.remove(LOCK)
        except OSError:
            pass


if __name__ == "__main__":
    main()
