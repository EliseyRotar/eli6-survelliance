#!/usr/bin/env python3
import urllib.request
import json
import os
import time

dossier = r"C:\Users\eli6-admin\Documents\eli6-surveillance\dossier_nolandda"
out_dir = f"{dossier}\\10_full_recon"

# Failed URLs - retry sequentially with delay
priorities = [
    "https://nolandda.org/",
    "https://nolandda.org/etc.html",
    "https://nolandda.org/sunlight.html",
    "https://nolandda.org/voyeurism.html",
    "https://nolandda.org/ascii.html",
    "https://nolandda.org/tools.html",
    "https://nolandda.org/friends.html",
    "https://nolandda.org/lnf.html",
    "https://nolandda.org/PALX/",
    "https://nolandda.org/PALX/index.html",
    "https://nolandda.org/PALX/members.html",
    "https://nolandda.org/PALX/adventures.html",
    "https://nolandda.org/pusite/index.html",
    "https://nolandda.org/pusite/weekly.html",
    "https://nolandda.org/pusite/daily.html",
    "https://nolandda.org/pusite/lnf.html",
    "https://nolandda.org/pusite/school.html",
    "https://nolandda.org/pusite/audio.html",
    "https://nolandda.org/pusite/search.html",
    "https://nolandda.org/pusite/stats.html",
    "https://nolandda.org/pusite/credit.html",
    "https://nolandda.org/pusite/emacs.html",
    "https://nolandda.org/pusite/emacs.intro.html",
    "https://nolandda.org/pusite/cs490-dsp/",
    "https://nolandda.org/pusite/voyeurism.html",
    "https://nolandda.org/xoomsite/",
    "https://nolandda.org/xoomsite/index.html",
    "https://nolandda.org/photos/index.html",
    "https://nolandda.org/projects/index.html",
    "https://nolandda.org/log/qblog_2017.09.11.23.53.28.html",
]

for url in priorities:
    fname = url.replace("https://nolandda.org/", "").replace("/", "_").strip("_") or "home"
    if not fname.endswith(".html"):
        fname = fname + ".html"
    outpath = f"{out_dir}\\nolandda_{fname}"
    if os.path.exists(outpath) and os.path.getsize(outpath) > 100:
        print(f"  SKIP {fname}")
        continue
    try:
        cdx_url = f"https://web.archive.org/cdx/search/cdx?url={url}&output=json&limit=1&filter=statuscode:200"
        req = urllib.request.Request(cdx_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            cd = json.loads(r.read())
            if not cd or len(cd) < 2:
                print(f"  NO_SNAP {url}")
                continue
            ts = cd[1][1]
            wayback_url = f"https://web.archive.org/web/{ts}id_/{url}"
            req = urllib.request.Request(wayback_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r2:
                d = r2.read()
                try:
                    text = d.decode("utf-8")
                except UnicodeDecodeError:
                    text = d.decode("latin-1", errors="replace")
                with open(outpath, "w", encoding="utf-8") as f:
                    f.write(text)
                print(f"  OK {fname} ({len(d)}, {ts[:8]})")
    except Exception as e:
        print(f"  ERR {url}: {str(e)[:60]}")
    time.sleep(2)  # rate limit

print("\nDone")