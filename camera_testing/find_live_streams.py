"""Probe cameras marked type=image in controllable_Webcams.csv for live video streams."""
from __future__ import annotations

import base64
import csv
import json
import os
import socket
import ssl
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse


CSV_PATH = r"C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv"
OUT_PATH = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\live_streams_found.json"
TIMEOUT = 5.0
MAX_WORKERS = 20

SKIP_IDX = {1, 2, 4}

SKIP_DESCRIPTION_NEEDLES = ("Wired New York",)

SKIP_URL_NEEDLES = (
    "youtube.com",
    "youtu.be",
    "bigsky",
)


@dataclass
class StreamProbe:
    idx: str
    original_url: str
    host: str
    scheme: str
    port: int
    base_url: str  # scheme://host:port
    auth: tuple[str, str] | None = None
    tried: list[dict[str, Any]] = field(default_factory=list)
    found: dict[str, Any] | None = None


# ----- CSV parsing ----------------------------------------------------------

def _parse_csv(path: str) -> list[dict[str, str]]:
    with open(path, "r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _normalize_url(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    # The url column may contain a couple of URLs separated by newlines; pick the first HTTP-ish one.
    parts = [p.strip() for p in raw.replace("\r", "").split("\n") if p.strip()]
    for p in parts:
        if p.lower().startswith(("http://", "https://", "rtsp://")):
            return p
    return parts[0] if parts else ""


def _derive_auth(row: dict[str, str]) -> tuple[str, str] | None:
    user = (row.get("auth_user") or "").strip()
    pwd = (row.get("auth_pass") or "").strip()
    if not user and not pwd:
        return None
    return (user or "admin", pwd or "")


def _is_skippable(idx: str, desc: str, url: str) -> str | None:
    try:
        n = int(idx)
    except (ValueError, TypeError):
        n = -1
    if n in SKIP_IDX:
        return f"idx={n} skip-listed"
    desc_l = (desc or "").lower()
    for needle in SKIP_DESCRIPTION_NEEDLES:
        if needle.lower() in desc_l:
            return f"description contains '{needle}'"
    url_l = (url or "").lower()
    for needle in SKIP_URL_NEEDLES:
        if needle in url_l:
            return f"url matches skip pattern '{needle}'"
    return None


# ----- URL candidate generation --------------------------------------------

def _strip_path(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.hostname}"
    if parsed.port:
        base += f":{parsed.port}"
    return base, parsed.path or "/"


def _http_url(base: str, path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path
    return base + path


def _candidate_paths(row: dict[str, str], base_path: str) -> list[str]:
    """Return an ordered list of candidate paths to probe (path-only)."""
    candidates: list[str] = []
    desc = (row.get("description") or "").lower()
    server = (row.get("server_header") or "").lower()
    brand = (row.get("brand") or "").lower()
    model = (row.get("model") or "").lower()

    is_axis = "axis" in desc or "axis" in brand or "axis" in model
    is_hikvision = "hikvision" in desc or "hikvision" in brand
    is_acti = "acti" in desc or "acti" in brand or "aca" in desc
    is_dahua = "dahua" in desc or "dahua" in brand
    is_hisilicon_hi35 = "hi3518" in desc or "hi3518" in brand or "hi3520" in desc or "hisilicon" in desc
    is_panasonic = ("panasonic" in desc or "panasonic" in brand
                    or "wv-" in desc or "bb-hcm" in desc or "wv-sp" in desc)
    is_canvb = "canon" in desc or "vb-c" in desc or "vb-c" in model
    is_stardot = "stardot" in desc or "stardot" in brand
    is_samsung = "samsung" in desc or "samsung" in brand

    paths = [
        # WebcamXP 5
        "/cam_1.cgi", "/cam_1.mjpg", "/cam_1.mjpeg",
        "/cam_2.cgi", "/cam_2.mjpg",
        # Generic IP cam MJPEG endpoints
        "/video.cgi", "/video.mjpg", "/mjpg/video.mjpg",
        "/livestream/1", "/streaming/channels/1",
        "/Streaming/Channels/101",
        # Hipcam HiSilicon
        "/11", "/12",
        "/web/tmpfs/video.mjpg", "/web/tmpfs/auto.jpg",
        # AXIS
        "/axis-cgi/mjpg/video.cgi",
        # ACTi
        "/cam0_0", "/av0_0",
        # Anything streaming
        "/live.m3u8", "/live.flv", "/live.mp4",
    ]

    if is_axis:
        paths = ["/axis-cgi/mjpg/video.cgi"] + paths

    if is_acti:
        paths = [
            "/cam0_0", "/av0_0",
            "/control/faststream.jpg?stream=full&fps=16",
            "/cgi-bin/faststream.jpg?stream=full&fps=16",
            "/mjpg/video.mjpg",
            "/video.cgi",
        ] + paths

    if is_hikvision:
        paths = paths + [
            "/Streaming/Channels/101",
            "/Streaming/Channels/1",
            "/ISAPI/Streaming/channels/1",
        ]

    if is_dahua or is_hisilicon_hi35:
        paths = [
            "/cgi-bin/faststream.jpg?stream=full&fps=16",
            "/control/faststream.jpg?stream=full&fps=16",
            "/mjpg/video.mjpg",
            "/video.cgi",
        ] + paths

    if is_panasonic:
        paths = paths + [
            "/-wvhttp-01-/video.cgi",
            "/cgi-bin/camera",
            "/CgiStart?page=Single&Language=0",
            "/live/oneshot.html",
            "/live/index.html?Language=0",
            "/live/index.html?Language=1",
        ]

    if is_canvb:
        paths = paths + ["/eng/liveView.cgi"]

    if is_stardot:
        paths = ["/nphMotionJpeg?Resolution=640x480", "/nphMotionJpeg"] + paths

    if is_samsung:
        paths = paths + ["/video.cgi", "/mjpg/1/video.mjpg"]

    seen: set[str] = set()
    out: list[str] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            out.append(p)
    # Don't include the original path (already known); the script is about finding NEW live URLs.
    if base_path in out:
        out.remove(base_path)
    return out


# ----- Probing ---------------------------------------------------------------

def _auth_header(auth: tuple[str, str] | None) -> dict[str, str] | None:
    if not auth:
        return None
    token = base64.b64encode(f"{auth[0]}:{auth[1]}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def _is_video_response(url: str, auth: tuple[str, str] | None, timeout: float) -> dict[str, Any]:
    """Send a GET request that aborts as soon as the headers are known.
    Returns a dict describing the response or error.
    """
    headers = {"User-Agent": "live-stream-finder/1.0", "Accept": "*/*"}
    if auth:
        headers.update(_auth_header(auth) or {})
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as exc:
        body_len = 0
        try:
            body_len = len(exc.read() or b"")
        except Exception:
            body_len = -1
        return {
            "ok": False,
            "url": url,
            "status": exc.code,
            "reason": exc.reason,
            "content_type": exc.headers.get("Content-Type") if exc.headers else "",
            "auth_used": bool(auth),
            "body_len": body_len,
        }
    except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionResetError) as exc:
        return {"ok": False, "url": url, "error": repr(exc), "auth_used": bool(auth)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "url": url, "error": repr(exc), "auth_used": bool(auth)}

    status = resp.status
    content_type = resp.headers.get("Content-Type", "") if resp.headers else ""
    # Read a small chunk to confirm streamy content.
    try:
        chunk = resp.read(2048)
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "url": url,
            "status": status,
            "content_type": content_type,
            "error": f"read-failed: {exc!r}",
            "auth_used": bool(auth),
        }
    finally:
        try:
            resp.close()
        except Exception:
            pass

    body_len = len(chunk)
    return {
        "ok": True,
        "url": url,
        "status": status,
        "content_type": content_type,
        "auth_used": bool(auth),
        "body_len": body_len,
        "body_preview": chunk,
    }


def _classify_response(resp: dict[str, Any], body_preview: bytes | None = None) -> dict[str, Any] | None:
    """Return a stream descriptor if the response looks like a live stream."""
    if not resp.get("ok"):
        return None
    status = resp.get("status")
    if status != 200:
        return None
    ct = (resp.get("content_type") or "").lower()
    url_lower = resp["url"].lower()
    body_len = resp.get("body_len", 0)
    body_text = (body_preview or b"").lstrip().lower()[:128]
    stream_type: str | None = None

    # Reject responses whose body looks like HTML (common when a cam returns a 404 page with 200 status).
    looks_html = body_text.startswith((b"<!doctype", b"<html", b"<!html", b"<head", b"<body"))

    if "multipart/x-mixed-replace" in ct:
        stream_type = "mjpeg"
    elif ct.startswith("video/") or ct.startswith("application/ogg") or ct.startswith("application/vnd.apple.mpegurl"):
        stream_type = "h264" if "h264" in ct or "h.264" in ct else "video"
    elif ct == "application/octet-stream" and body_len > 64 and not looks_html:
        stream_type = "video"
    elif url_lower.endswith(".m3u8"):
        # Must look like an actual HLS playlist (starts with #EXTM3U) and content-type should be m3u8-ish.
        if (ct.startswith("application/vnd.apple.mpegurl")
                or ct == "application/x-mpegurl"
                or ct == "audio/x-mpegurl"):
            stream_type = "hls"
        elif body_text.startswith(b"#extm3u"):
            stream_type = "hls"
        else:
            return None
    elif url_lower.endswith(".flv"):
        if not looks_html and (ct.startswith("video/") or ct == "application/octet-stream" or ct == "video/x-flv"):
            stream_type = "flv"
    elif url_lower.endswith(".mp4"):
        if not looks_html and (ct.startswith("video/") or ct == "application/octet-stream"):
            stream_type = "mp4"

    if not stream_type:
        return None

    return {
        "found_live_url": resp["url"],
        "stream_type": stream_type,
        "content_type": ct,
        "auth_used": resp.get("auth_used", False),
        "evidence_status": status,
        "evidence_body_len": body_len,
    }


def _tcp_connect(host: str, port: int, timeout: float) -> tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, "tcp-open"
    except (socket.timeout, ConnectionRefusedError, OSError) as exc:
        return False, repr(exc)


def _probe_rtsp(probe: StreamProbe, candidate_paths: list[str]) -> dict[str, Any] | None:
    rtsp_port = 554
    ok, info = _tcp_connect(probe.host, rtsp_port, TIMEOUT)
    if not ok:
        probe.tried.append({"url": f"rtsp://{probe.host}:{rtsp_port}/", "ok": False, "info": info})
        return None

    # Build credentialed / non-credentialed RTSP URLs.
    cred = probe.auth
    found: dict[str, Any] | None = None
    for path in candidate_paths:
        for use_creds in (False, True) if cred else (False,):
            if use_creds:
                url = f"rtsp://{cred[0]}:{cred[1]}@{probe.host}:{rtsp_port}{path}"
            else:
                url = f"rtsp://{probe.host}:{rtsp_port}{path}"
            try:
                req = urllib.request.Request(url, method="OPTIONS")
                resp = urllib.request.urlopen(req, timeout=TIMEOUT)
                ctype = resp.headers.get("Content-Type", "") if resp.headers else ""
                body = resp.read(256)
                probe.tried.append({
                    "url": url,
                    "ok": True,
                    "status": resp.status,
                    "content_type": ctype,
                    "body_len": len(body),
                })
                if resp.status in (200, 451):
                    found = {
                        "found_live_url": url,
                        "stream_type": "rtsp",
                        "content_type": ctype or "application/sdp",
                        "auth_used": use_creds,
                        "evidence_status": resp.status,
                    }
                    break
            except urllib.error.HTTPError as exc:
                probe.tried.append({
                    "url": url,
                    "ok": False,
                    "status": exc.code,
                    "reason": exc.reason,
                })
                if exc.code in (401, 403):
                    # alive server, just needs auth (already tried both)
                    found = {
                        "found_live_url": url,
                        "stream_type": "rtsp",
                        "content_type": exc.headers.get("Content-Type", "") if exc.headers else "",
                        "auth_used": use_creds,
                        "evidence_status": exc.code,
                    }
                    break
            except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionResetError, OSError) as exc:
                probe.tried.append({"url": url, "ok": False, "info": repr(exc)})
                continue
            except Exception as exc:  # noqa: BLE001
                probe.tried.append({"url": url, "ok": False, "info": repr(exc)})
                continue
        if found:
            break
    return found


# ----- Per-camera probing ---------------------------------------------------

def probe_camera(row: dict[str, str]) -> dict[str, Any]:
    idx = (row.get("idx") or "").strip()
    url_raw = _normalize_url(row.get("url") or "")
    desc = row.get("description") or ""

    base_record: dict[str, Any] = {
        "idx": idx,
        "original_url": url_raw,
        "found_live_url": None,
        "stream_type": None,
    }

    if not url_raw:
        base_record["skipped"] = "no-url"
        return base_record

    skip_reason = _is_skippable(idx, desc, url_raw)
    if skip_reason:
        base_record["skipped"] = skip_reason
        return base_record

    parsed = urlparse(url_raw)
    if not parsed.scheme or not parsed.hostname:
        base_record["skipped"] = "unparsable-url"
        return base_record

    base = f"{parsed.scheme}://{parsed.hostname}"
    if parsed.port:
        base += f":{parsed.port}"
    base_path = parsed.path or "/"

    auth = _derive_auth(row)

    probe = StreamProbe(
        idx=idx,
        original_url=url_raw,
        host=parsed.hostname,
        scheme=parsed.scheme,
        port=parsed.port or (443 if parsed.scheme == "https" else 80),
        base_url=base,
        auth=auth,
    )

    # Phase 1: HTTP/HTTPS path candidates.
    candidates = _candidate_paths(row, base_path)
    # Cap to avoid hammering anything; ~30 per host is plenty.
    candidates = candidates[:30]

    for path in candidates:
        url = _http_url(base, path)
        auth_attempts: list[tuple[str, tuple[str, str] | None]] = [(url, None)]
        if auth and not url.lower().__contains__("/axis-cgi/jpg/"):
            # Try with auth if first attempt failed (we still check both, but no point if path is /axis-cgi/jpg/image.cgi).
            auth_attempts.append((url, auth))
        for target, use_auth in auth_attempts:
            resp = _is_video_response(target, use_auth, TIMEOUT)
            probe.tried.append({"url": target, **({"auth_used": bool(use_auth)} if use_auth else {}), **{k: v for k, v in resp.items() if k != "url"}})
            found = _classify_response(resp, resp.get("body_preview"))
            if found:
                probe.found = found
                break
        if probe.found:
            break

    # Phase 2: RTSP probes for HiSilicon / generic cams.
    if not probe.found:
        rtsp_candidates = [
            "/11", "/12", "/live/0", "/live/1",
            "/Streaming/Channels/101", "/Streaming/Channels/1",
            "/Streaming/tracks/101", "/ch01/0/main/av_stream",
            "/av0_0", "/mpeg4",
        ]
        found = _probe_rtsp(probe, rtsp_candidates)
        if found:
            probe.found = found

    base_record.update({
        "found_live_url": probe.found["found_live_url"] if probe.found else None,
        "stream_type": probe.found["stream_type"] if probe.found else None,
        "content_type": probe.found.get("content_type") if probe.found else None,
        "auth_used": probe.found.get("auth_used") if probe.found else None,
        "evidence_status": probe.found.get("evidence_status") if probe.found else None,
        "evidence_body_len": probe.found.get("evidence_body_len") if probe.found else None,
        "candidates_tried": len(probe.tried),
        "tried_sample": [{k: v for k, v in t.items() if k != "body_preview"} for t in probe.tried[:8]],
    })
    return base_record


# ----- Main -----------------------------------------------------------------

def main() -> int:
    rows = _parse_csv(CSV_PATH)
    image_rows = []
    for r in rows:
        if (r.get("type") or "").strip().lower() != "image":
            continue
        idx = (r.get("idx") or "").strip()
        if not idx:
            continue
        try:
            int(idx)
        except ValueError:
            continue
        image_rows.append(r)

    print(f"image-type rows in CSV: {len(image_rows)}", file=sys.stderr)

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        future_to_idx = {ex.submit(probe_camera, row): row["idx"] for row in image_rows}
        for fut in as_completed(future_to_idx):
            idx = future_to_idx[fut]
            try:
                rec = fut.result()
            except Exception as exc:  # noqa: BLE001
                rec = {"idx": idx, "error": repr(exc)}
            results.append(rec)
            flag = "LIVE" if rec.get("found_live_url") else "----"
            print(f"  [{flag}] idx={idx} url={rec.get('original_url')!r} -> {rec.get('found_live_url')!r} ({rec.get('stream_type')})", file=sys.stderr)

    # Stable order by idx.
    def _key(r: dict[str, Any]) -> int:
        try:
            return int(r.get("idx") or "0")
        except ValueError:
            return 0

    results.sort(key=_key)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)

    found_count = sum(1 for r in results if r.get("found_live_url"))
    skipped_count = sum(1 for r in results if r.get("skipped"))
    print(f"\nProcessed: {len(results)} image-type cams", file=sys.stderr)
    print(f"Live streams found: {found_count}", file=sys.stderr)
    print(f"Skipped: {skipped_count}", file=sys.stderr)
    print(f"Saved to: {OUT_PATH}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
