# -*- coding: utf-8 -*-
"""Session 47: youtube watch-page analysis for found webcam embeds."""
import json
import re
import urllib.request
import urllib.error

ROOT = r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}


def fetch(url, timeout=40):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read(500000)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read(4000)
    except Exception as e:
        return None, {}, repr(e).encode()


yts = json.load(open(ROOT + r"\_es_webcam_yt_ids.json", encoding="utf-8"))
print("ids:", list(yts.keys()))
out = {}
for vid, meta in yts.items():
    st, h, b = fetch(f"https://www.youtube.com/watch?v={vid}")
    print("\n", vid, "->", st, len(b))
    if st != 200:
        continue
    t = b.decode("utf-8", "replace")
    rec = {"label": (meta.get("labels") or [""])[0]}
    m = re.search(r'"title":"([^"]{3,120})","lengthSeconds', t)
    m2 = re.search(r'<meta name="title" content="([^"]+)"', t)
    rec["yt_title"] = (m2.group(1) if m2 else (m.group(1) if m else ""))
    m = re.search(r'"author":"([^"]+)"', t)
    rec["author"] = m.group(1) if m else ""
    m = re.search(r'"channelId":"([^"]+)"', t)
    rec["channel_id"] = m.group(1) if m else ""
    m = re.search(r'"ownerChannelName":"([^"]+)"', t)
    rec["owner"] = m.group(1) if m else ""
    rec["isLive"] = '"isLive":true' in t or '"isLiveContent":true' in t
    rec["isLiveNow"] = '"isLiveNow":true' in t
    m = re.search(r'"publishDate":"([^"]+)"', t)
    rec["publish"] = m.group(1) if m else ""
    m = re.search(r'"uploadDate":"([^"]+)"', t)
    rec["upload"] = m.group(1) if m else ""
    # channel url
    m = re.search(r'"canonicalBaseUrl":"/(@[^"]+)"', t)
    rec["channel_url"] = "https://www.youtube.com" + m.group(1) if m else ""
    out[vid] = rec
    print("  ", json.dumps(rec, ensure_ascii=False))

json.dump(out, open(ROOT + r"\_es_yt_analysis.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
