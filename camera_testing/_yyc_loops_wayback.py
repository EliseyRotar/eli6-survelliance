# -*- coding: utf-8 -*-
"""Session 48e: Wayback multi-year loop videos (MP4+GIF) for Calgary cams.

Per loc: CDX digest-collapsed snapshots -> download via /web/<ts>id_/ raw ->
frames_wayback/ sorted by time -> wayback.mp4 (2 fps) + wayback.gif.
Cams with <2 frames skipped. Polite: small pool + delay.
"""
import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance"
OUT = os.path.join(ROOT, "web_viewer", "static", "loops", "yyc")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
LOCS = list(range(0, 224))


def curl_text(url, timeout=70):
    p = subprocess.run(["curl", "-sL", "-A", UA, "--max-time", str(timeout), url],
                       capture_output=True, timeout=timeout + 10)
    return p.stdout


def get_cdx(loc):
    url = ("https://web.archive.org/cdx/search/cdx?url=trafficcam.calgary.ca/loc%d.jpg"
           "&output=json&fl=timestamp,statuscode,mimetype&collapse=digest&filter=statuscode:200"
           "&filter=mimetype:image/jpeg" % loc)
    raw = curl_text(url, 70)
    try:
        d = json.loads(raw.decode("utf-8", "replace"))
        rows = d[1:] if len(d) > 1 else []
        return [r[0] for r in rows]
    except Exception:
        return []


def download_snap(loc, ts, out_path, timeout=50):
    url = "https://web.archive.org/web/%sid_/https://trafficcam.calgary.ca/loc%d.jpg" % (ts, loc)
    for attempt in range(4):
        p = subprocess.run(["curl", "-sL", "-A", UA, "--max-time", str(timeout),
                            "-o", out_path, "-w", "%{http_code}", url],
                           capture_output=True, text=True, timeout=timeout + 8)
        code = (p.stdout or "").strip()
        if code == "200" and os.path.exists(out_path):
            with open(out_path, "rb") as f:
                if f.read(2) == b"\xff\xd8":
                    time.sleep(5.0)
                    return True
        if code in ("429", "503", "520", "523", "524"):
            time.sleep(60 * (attempt + 1))
            continue
        time.sleep(3.0)
        break
    if os.path.exists(out_path):
        try:
            os.remove(out_path)
        except OSError:
            pass
    return False


def build_cam(loc):
    d = os.path.join(OUT, str(loc))
    fdir = os.path.join(d, "frames_wayback")
    os.makedirs(fdir, exist_ok=True)
    # reuse existing frames if rerun
    existing = sorted(f for f in os.listdir(fdir) if f.endswith(".jpg"))
    if len(existing) >= 2:
        stamps = ["cached"] * len(existing)
    else:
        stamps = get_cdx(loc)
        time.sleep(1.0)
        if not stamps:
            time.sleep(12)
            stamps = get_cdx(loc)
            time.sleep(1.0)
        got = []
        for i, ts in enumerate(stamps):
            out = os.path.join(fdir, "%04d.jpg" % i)
            if os.path.exists(out):
                got.append(ts)
                continue
            if download_snap(loc, ts, out):
                got.append(ts)
            time.sleep(0.8)
        stamps = got
        # renumber sequential
        files = sorted(f for f in os.listdir(fdir) if f.endswith(".jpg"))
        for i, f in enumerate(files):
            t = "%04d.jpg" % i
            if f != t:
                os.replace(os.path.join(fdir, f), os.path.join(fdir, t))
        existing = sorted(f for f in os.listdir(fdir) if f.endswith(".jpg"))
    if len(existing) < 2:
        return loc, "skip(<2)", len(existing)
    mp4 = os.path.join(d, "wayback.mp4")
    gif = os.path.join(d, "wayback.gif")
    p1 = subprocess.run(["ffmpeg", "-y", "-framerate", "2", "-i", os.path.join(fdir, "%04d.jpg"),
                         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                         "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                         mp4], capture_output=True, timeout=180)
    p2 = subprocess.run(["ffmpeg", "-y", "-framerate", "2", "-i", os.path.join(fdir, "%04d.jpg"),
                         "-vf", "fps=2,scale=640:-2:flags=lanczos,split[s0][s1];"
                                "[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer",
                         gif], capture_output=True, timeout=300)
    ok1 = p1.returncode == 0 and os.path.exists(mp4)
    ok2 = p2.returncode == 0 and os.path.exists(gif)
    return loc, ("ok" if ok1 and ok2 else "mp4=%s gif=%s" % (ok1, ok2)), len(existing)


def main():
    results = {}
    with ThreadPoolExecutor(max_workers=1) as ex:
        futs = {ex.submit(build_cam, loc): loc for loc in LOCS}
        for f in as_completed(futs):
            loc, status, n = f.result()
            results[loc] = [status, n]
            print("loc%-4d %-10s frames=%d" % (loc, status, n), flush=True)
    ok = sum(1 for v in results.values() if v[0] == "ok")
    print("\nSUMMARY wayback ok=%d/%d" % (ok, len(LOCS)))
    json.dump({str(k): v for k, v in results.items()},
              open(os.path.join(ROOT, "camera_testing", "yyc_wayback_loops.json"), "w"), indent=1)
    # partial-save inside loop not needed: frames cached on disk incrementally


if __name__ == "__main__":
    main()
