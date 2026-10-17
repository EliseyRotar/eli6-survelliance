# -*- coding: utf-8 -*-
"""Session 47: yt oembed + full-page isLive."""
import json
import re
import urllib.request
import urllib.error

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}


def fetch(url, timeout=45, cap=3000000):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(cap)
    except urllib.error.HTTPError as e:
        return e.code, e.read(4000)
    except Exception as e:
        return None, repr(e).encode()


yts = json.load(open(ROOT + r"\_es_webcam_yt_ids.json", encoding="utf-8"))
out = {}
for vid, meta in yts.items():
    rec = {"label": (meta.get("labels") or [""])[0]}
    # oEmbed
    st, b = fetch(f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch%3Fv%3D{vid}&format=json")
    if st == 200:
        try:
            d = json.loads(b.decode())
            rec["yt_title"] = d.get("title", "")
            rec["author"] = d.get("author_name", "")
            rec["author_url"] = d.get("author_url", "")
        except Exception as e:
            rec["oembed_err"] = str(e)
    else:
        rec["oembed_status"] = st
        rec["oembed_body"] = b[:150].decode("utf-8", "replace")
    # full watch page for isLive
    st, b = fetch(f"https://www.youtube.com/watch?v={vid}&hl=en")
    if st == 200:
        t = b.decode("utf-8", "replace")
        rec["isLive"] = '"isLive":true' in t
        rec["isLiveNow"] = '"isLiveNow":true' in t
        m = re.search(r'"startTimestamp":"([^"]+)"', t)
        rec["startTimestamp"] = m.group(1) if m else ""
        m = re.search(r'"channelId":"(UC[\w-]{22})"', t)
        rec["channel_id"] = m.group(1) if m else ""
        m = re.search(r'"canonicalBaseUrl":"(/@[^"]+)"', t)
        rec["channel_url"] = "https://www.youtube.com" + m.group(1) if m else ""
        m = re.search(r'"uploadDate":"([^"]+)"', t)
        rec["upload"] = m.group(1) if m else ""
        rec["viewCount"] = (re.search(r'"viewCount":"(\d+)"', t) or type("", (), {"group": lambda s, i: ""})()).group(1) if '"viewCount"' in t else ""
    out[vid] = rec
    print(vid, json.dumps(rec, ensure_ascii=False), flush=True)

json.dump(out, open(ROOT + r"\_es_yt_analysis.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
