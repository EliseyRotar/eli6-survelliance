# -*- coding: utf-8 -*-
"""Session 49: enumerate every CCTV Guesser camera.

/api/cameras returns 1 RANDOM camera per request (no params honored).
Coupon-collector: hammer politely, dedupe by id, stop when a long tail
produces (almost) no new ids. Also harvests cam_id seeds from the
readable supabase `scoreboard` table (played cams only).

Outputs: camera_testing/cctvguesser_raw.jsonl (+ .csv at the end)
Log:     camera_testing/cctvguesser.log
"""
import csv
import json
import os
import threading
import time
import urllib.request
from datetime import datetime

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
API = "https://cctvguesser.com/api/cameras"
OUT_JSONL = os.path.join(ROOT, "camera_testing", "cctvguesser_raw.jsonl")
OUT_CSV = os.path.join(ROOT, "camera_testing", "cctvguesser_cameras.csv")
LOG = os.path.join(ROOT, "camera_testing", "cctvguesser.log")
SB_KEY = "sb_publishable_a3S9HZafxmYaXW_HF8PB6w_JeCKU8WM"
SB_URL = "https://xuasrjruuvrnatkeyjlg.supabase.co/rest/v1/scoreboard"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

MAX_WORKERS = 4
IDLE_STOP = 1500          # stop after this many requests with no new id
TAIL_WATCH = 300          # log detail when this few requests remain in tail
REQ_DELAY = 0.12          # per-worker politeness delay

lock = threading.Lock()
seen = {}                 # id -> record
requests_n = 0
idle_n = 0
stop_flag = False
t0 = time.time()


def log(msg):
    line = "%s %s" % (datetime.now().strftime("%H:%M:%S"), msg)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def http_get(url, headers=None, timeout=20):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def harvest_scoreboard():
    try:
        headers = {"apikey": SB_KEY, "Authorization": "Bearer " + SB_KEY,
                   "Prefer": "count=exact", "User-Agent": UA}
        req = urllib.request.Request(SB_URL + "?select=cam_id&limit=5000", headers=headers)
        with urllib.request.urlopen(req, timeout=25) as r:
            total = 0
            cr = r.headers.get("content-range")
            if cr and "/" in cr:
                total = int(cr.split("/")[1])
            rows = json.loads(r.read())
        ids = sorted({row["cam_id"] for row in rows if row.get("cam_id")})
        with open(os.path.join(ROOT, "camera_testing", "cctvguesser_scoreboard_cids.txt"),
                  "w", encoding="utf-8") as f:
            f.write("\n".join(ids))
        log("scoreboard: %d rows total, %d distinct cam_ids (played subset)"
            % (total, len(ids)))
    except Exception as e:
        log("scoreboard harvest failed: %r" % e)


def worker(wid):
    global requests_n, idle_n, stop_flag
    while not stop_flag:
        try:
            raw = http_get(API, timeout=20)
            recs = json.loads(raw)
            rec = recs[0] if isinstance(recs, list) and recs else None
        except Exception:
            rec = None
            time.sleep(0.5)
        with lock:
            requests_n += 1
            new = False
            if rec and rec.get("id"):
                if rec["id"] not in seen:
                    seen[rec["id"]] = rec
                    new = True
                    idle_n = 0
                    with open(OUT_JSONL, "a", encoding="utf-8") as f:
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                else:
                    idle_n += 1
            else:
                idle_n += 1
            n_req, n_seen, n_idle = requests_n, len(seen), idle_n
            if n_seen and n_seen % 100 < 2 and new:
                log("unique=%d requests=%d (%.1f req/s) NEW" %
                    (n_seen, n_req, n_req / max(1, time.time() - t0)))
            if n_idle >= IDLE_STOP:
                stop_flag = True
        time.sleep(REQ_DELAY)


def write_csv():
    with open(OUT_JSONL, "r", encoding="utf-8") as f:
        rows = [json.loads(l) for l in f if l.strip()]
    cols = ["id", "name", "url", "lat", "lng", "country", "country_code",
            "state", "city", "display_name", "blackouts"]
    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in sorted(rows, key=lambda x: (x.get("country_code") or "",
                                             x.get("name") or "")):
            r = dict(r)
            r["blackouts"] = json.dumps(r.get("blackouts"), separators=(",", ":"))
            w.writerow(r)
    return len(rows)


def main():
    if os.path.exists(OUT_JSONL):
        with open(OUT_JSONL, "r", encoding="utf-8") as f:
            for l in f:
                if l.strip():
                    rec = json.loads(l)
                    if rec.get("id"):
                        seen[rec["id"]] = rec
    log("collector start: resuming with %d known" % len(seen))
    harvest_scoreboard()
    threads = [threading.Thread(target=worker, args=(i,), daemon=True)
               for i in range(MAX_WORKERS)]
    for t in threads:
        t.start()
    while not stop_flag:
        time.sleep(30)
        with lock:
            log("progress: unique=%d requests=%d idle=%d (%.1f req/s)" %
                (len(seen), requests_n, idle_n,
                 requests_n / max(1, time.time() - t0)))
    n = write_csv()
    log("DONE: %d unique cameras -> %s (requests=%d, %.0f min)" %
        (n, OUT_CSV, requests_n, (time.time() - t0) / 60))


if __name__ == "__main__":
    main()
