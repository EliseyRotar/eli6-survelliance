#!/usr/bin/env python3
"""
IP / Host / URL availability checker (IP-camera aware).

For each target, runs probes in this order and stops at the first that
succeeds:

  1. HTTP GET on the original URL with a browser-like User-Agent.
     Counts as success on 200/206/416 with real bytes, OR any 2xx/3xx/4xx/5xx
     when --loose is set.
  2. HTTP GET on the bare host root (e.g. http://cam.example.com/) — catches
     aggregator sites whose "url" column is a sub-path that 404s.
  3. TCP handshake on common camera/web ports.
  4. ICMP ping (skippable with --no-ping).

A response is also considered "camera-like" when:
  - Content-Type is image/jpeg, multipart/x-mixed-replace, video/mjpeg, or
    application/octet-stream AND the first bytes look like JPEG (FF D8 FF).
  - The body contains HTML with camera/streaming keywords (for aggregator
    sites that list live cams without serving one directly).

Usage:
    python check_ip_availability.py -f webcam_urls.txt --no-ping
    python check_ip_availability.py -f webcam_urls.txt --no-ping --loose
"""

import argparse
import html
import json
import re
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urlunparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

IS_WINDOWS = sys.platform.startswith("win")

DEFAULT_TCP_PORTS = (80, 443, 554, 8000, 8080, 8443)
HTTP_TIMEOUT = 8.0
PING_TIMEOUT_S = 2

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

CAMERA_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/pjpeg",
    "multipart/x-mixed-replace",
    "video/mjpeg",
    "application/octet-stream",
}

# HTML keywords that strongly suggest the page IS a webcam listing/embed.
CAMERA_HTML_KEYWORDS = (
    "mjpeg", "mjpg", "viewerframe", "axis-cgi", "image.cgi",
    "livecam", "live cam", "live-cam", "webcam", "ip camera",
    "<img ", "<iframe", "video streaming", "live video",
    "controllablewebcams", "cctv", "surveillance",
)

# Aggregator-style domains that we should always treat as "alive" when they
# return 200 OK, even if the page doesn't match the camera keyword list.
KNOWN_AGGREGATORS = {
    "www.opentopia.com", "www.skylinewebcams.com", "www.earthcam.com",
    "www.webcamplaza.net", "webcamplaza.net", "www.camscape.com",
    "opentopia.com", "skylinewebcams.com", "earthcam.com",
    "webcamplaza.net", "camscape.com", "livesecuritycams.com",
    "spyeazy.net", "www.ipetcompanion.com", "www.flatcreekinn.com",
    "www.abbeyroad.com", "www.vanaqua.org", "www.divecommander.com",
    "watch.sniffdoghotel.com", "www.sdzsafaripark.org",
    "www.schooners.com", "obhotel.com", "www.wanetawebcam.com",
    "www.super807.co.jp", "www.tour.pitt.edu",
    "hdtv.webcam.nl", "www.bmwbeachlounge.be", "www.scheveningenlive.nl",
    "www.abbeyroad.com", "watchthewater.org", "webcam.teuva.fi",
    "live.mila.is", "www.unions.missouri.edu", "www.lakefrontcam.com",
    "www.novascotiawebcams.com", "webcamlocator.net", "www.rgns.com",
    "www.rit.edu", "www.rit.edu/webcam",
}


def decode_url(target):
    """Decode HTML entities (`&amp;` etc.) often present in scraped URLs."""
    return html.unescape(target)


def normalize_bare_host(target):
    """If the target has no scheme, default to http://."""
    if "://" in target:
        return target
    if re.fullmatch(r"[^\s/:]+:\d+\S*", target):
        return f"http://{target}"
    if re.fullmatch(r"[^\s/]+", target):
        return f"http://{target}"
    return target


def make_session():
    """A requests session that retries on transient errors and follows redirects."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "image/jpeg,multipart/x-mixed-replace,video/mjpeg,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Range": "bytes=0-2047",
    })
    retries = Retry(
        total=2, backoff_factor=0.5,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "HEAD"]),
    )
    adapter = HTTPAdapter(max_retries=retries, pool_maxsize=10)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s


def ping_host(host):
    if IS_WINDOWS:
        cmd = ["ping", "-n", "1", "-w", str(PING_TIMEOUT_S * 1000), host]
    else:
        cmd = ["ping", "-c", "1", "-W", str(PING_TIMEOUT_S), host]
    start = time.monotonic()
    try:
        result = subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=PING_TIMEOUT_S + 1,
        )
        latency_ms = (time.monotonic() - start) * 1000.0
        return result.returncode == 0, round(latency_ms, 1), None
    except subprocess.TimeoutExpired:
        return False, None, "ping timeout"
    except FileNotFoundError:
        return False, None, "ping not installed"
    except Exception as exc:
        return False, None, str(exc)


def tcp_probe(host, port):
    start = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=2.0):
            return True, round((time.monotonic() - start) * 1000.0, 1)
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False, None


def http_probe(session, url):
    """GET the URL with the prepared session. Returns
    (ok, status, latency_ms, content_type, body_or_None, reason)."""
    start = time.monotonic()
    try:
        resp = session.get(url, timeout=HTTP_TIMEOUT, stream=True,
                           allow_redirects=True)
        chunks = []
        total = 0
        for chunk in resp.iter_content(chunk_size=512):
            if chunk:
                chunks.append(chunk)
                total += len(chunk)
                if total >= 2048:
                    break
        resp.close()
        latency_ms = (time.monotonic() - start) * 1000.0
        ctype = resp.headers.get("content-type", "")
        body = b"".join(chunks)
        return True, resp.status_code, round(latency_ms, 1), ctype, body, None
    except requests.exceptions.SSLError as exc:
        return False, None, None, None, None, f"ssl: {exc}"
    except requests.exceptions.ReadTimeout:
        return False, None, None, None, None, "timeout"
    except requests.exceptions.ConnectionError as exc:
        return False, None, None, None, None, f"connection: {exc}"
    except requests.exceptions.RequestException as exc:
        return False, None, None, None, None, str(exc)


def looks_like_camera(ctype, body, host):
    """Decide if a response looks like a camera endpoint."""
    if not ctype:
        return False
    ct = ctype.lower().split(";")[0].strip()
    if ct in CAMERA_CONTENT_TYPES:
        if ct.startswith("image/"):
            return body.startswith(b"\xff\xd8")
        return True  # multipart or octet-stream
    # Aggregator HTML: keyword match or known host.
    if ct.startswith("text/html"):
        text = body.decode("utf-8", errors="ignore").lower()
        if any(k in text for k in CAMERA_HTML_KEYWORDS):
            return True
        if host in KNOWN_AGGREGATORS:
            return True
    return False


def http_root_probe(session, host):
    """Try the bare host root on http and https — for aggregator sites whose
    sub-path URL 404s but the domain itself is alive."""
    last_err = None
    for scheme in ("https", "http"):
        url = f"{scheme}://{host}/"
        try:
            resp = session.get(url, timeout=HTTP_TIMEOUT, stream=True,
                               allow_redirects=True)
            chunks = []
            total = 0
            for chunk in resp.iter_content(chunk_size=512):
                if chunk:
                    chunks.append(chunk)
                    total += len(chunk)
                    if total >= 2048:
                        break
            resp.close()
            return True, resp.status_code, resp.headers.get("content-type", ""), \
                b"".join(chunks), None
        except requests.exceptions.RequestException as exc:
            last_err = str(exc)
    return False, None, None, None, last_err


def check_target(target, *, use_ping=True, use_http=True, strict=False,
                 loose=False, session=None):
    target = decode_url(target)
    target = normalize_bare_host(target)
    parsed = urlparse(target)
    host = parsed.hostname or ""
    port = parsed.port

    result = {
        "target": target,
        "host": host,
        "port": port,
        "available": False,
        "probe": None,
        "latency_ms": None,
        "error": None,
        "http_status": None,
        "content_type": None,
        "camera_like": False,
        "final_url": None,
    }
    if not host:
        result["error"] = "no host"
        return result

    if session is None:
        session = make_session()

    if use_http:
        # 1. Original URL
        ok, status, latency, ctype, body, err = http_probe(session, target)
        if ok and status is not None:
            result.update(http_status=status, content_type=ctype,
                          latency_ms=latency, final_url=target)
            if 200 <= status < 400:
                cam = looks_like_camera(ctype, body, host)
                result["camera_like"] = cam
                result["available"] = True
                result["probe"] = "http-orig"
                return result
            if loose:
                result["available"] = True
                result["probe"] = "http-orig"
                result["camera_like"] = looks_like_camera(ctype, body, host)
                return result
            result["error"] = f"http {status}"
            return result
        else:
            result["error"] = err

        # 2. Bare host root fallback (handles aggregator sites where the
        #    sub-path URL is broken but the domain serves a landing page).
        if host and (parsed.path not in ("", "/")):
            ok2, status2, ctype2, body2, err2 = http_root_probe(session, host)
            if ok2 and status2 is not None:
                result.update(http_status=status2, content_type=ctype2,
                              latency_ms=latency, final_url=target)
                if 200 <= status2 < 400:
                    cam2 = looks_like_camera(ctype2, body2, host)
                    result["camera_like"] = cam2
                    if cam2 or loose:
                        result["available"] = True
                        result["probe"] = "http-root"
                        return result
                    # Even if the root isn't a camera listing, the host
                    # responded — record it but don't claim "available".
                elif loose and status2:
                    result["available"] = True
                    result["probe"] = "http-root"
                    return result

    # 3. TCP probe
    ports_to_try = [port] if port else []
    ports_to_try += [p for p in DEFAULT_TCP_PORTS if p != port]
    best = None
    with ThreadPoolExecutor(max_workers=max(1, len(ports_to_try))) as pool:
        futures = {pool.submit(tcp_probe, host, p): p for p in ports_to_try}
        for fut in as_completed(futures):
            ok, latency = fut.result()
            if ok and (best is None or (latency or 1e9) < (best[1] or 1e9)):
                best = (futures[fut], latency)
    if best is not None:
        result.update(available=True, probe="tcp", port=best[0],
                      latency_ms=best[1])
        return result

    # 4. ICMP ping
    if use_ping:
        ok, latency, err = ping_host(host)
        if ok:
            result.update(available=True, probe="ping", latency_ms=latency)
            return result
        if not result["error"]:
            result["error"] = err

    if not result["error"]:
        result["error"] = "all probes failed"
    return result


def read_inputs(args):
    targets = list(args.target or [])
    if args.file:
        with open(args.file, "r", encoding="utf-8") as fh:
            targets.extend(line.strip() for line in fh if line.strip())
    if not sys.stdin.isatty():
        targets.extend(line.strip() for line in sys.stdin if line.strip())
    return targets


def format_row(result):
    mark = "OK " if result["available"] else "FAIL"
    probe = result["probe"] or "-"
    latency = f"{result['latency_ms']}ms" if result["latency_ms"] is not None else "-"
    target = result["target"]
    if len(target) > 60:
        target = target[:57] + "..."
    detail = ""
    if result.get("http_status") is not None:
        detail = f" [HTTP {result['http_status']}]"
    if result.get("content_type"):
        ct = result["content_type"].split(";")[0]
        detail += f" ({ct}{'*' if result.get('camera_like') else ''})"
    if not result["available"] and result["error"]:
        detail += f" ({result['error']})"
    return f"[{mark}] {target:<60} probe={probe:<11} {latency:>8}{detail}"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check whether IPs / hosts / URLs are reachable.",
    )
    parser.add_argument("target", nargs="*")
    parser.add_argument("-f", "--file")
    parser.add_argument("--no-ping", action="store_true")
    parser.add_argument("--no-http", action="store_true")
    parser.add_argument("--http", dest="force_http", action="store_true")
    parser.add_argument("--loose", action="store_true",
                        help="Mark any HTTP response as available")
    parser.add_argument("-w", "--workers", type=int, default=30)
    parser.add_argument("-j", "--json", action="store_true")
    parser.add_argument("-q", "--quiet", action="store_true")
    parser.add_argument("-o", "--output")

    args = parser.parse_args(argv)
    targets = read_inputs(args)
    if not targets:
        parser.error("no targets provided")

    use_http = (not args.no_http) or args.force_http
    session = make_session()

    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(check_target, t,
                        use_ping=not args.no_ping,
                        use_http=use_http,
                        loose=args.loose,
                        session=session): t
            for t in targets
        }
        for fut in as_completed(futures):
            results.append(fut.result())

    order = {t: i for i, t in enumerate(targets)}
    results.sort(key=lambda r: order.get(r["target"], 0))

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=2)
    if args.json:
        json.dump(results, sys.stdout, indent=2)
        sys.stdout.write("\n")
    elif not args.output:
        rows = [r for r in results if not args.quiet or not r["available"]]
        for r in rows:
            print(format_row(r))
        total = len(results)
        up = sum(1 for r in results if r["available"])
        cam = sum(1 for r in results if r.get("camera_like"))
        print(f"\n{up}/{total} reachable  |  {cam} camera-like")

    return 0 if all(r["available"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
