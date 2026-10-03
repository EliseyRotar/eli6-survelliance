#!/usr/bin/env python3
import urllib.request
import json
import re
import time

dossier = r"C:\Users\eli6-admin\Documents\eli6-surveillance\dossier_nolandda"

# High-value pages to pull from Wayback
priority_urls = [
    # Resume - critical
    ("https://nolandda.org/resume/", "resume.html"),
    # Blog
    ("https://nolandda.org/log/", "log.html"),
    ("https://nolandda.org/log/archive.html", "log_archive.html"),
    # About pages
    ("https://nolandda.org/about.html", "about.html"),
    # Projects
    ("https://nolandda.org/projects/", "projects.html"),
    ("https://nolandda.org/projects/WinFork.cpp.html", "WinFork.html"),
    # RPG campaigns (Dan ran tabletop)
    ("https://nolandda.org/rpg/ironhold/index.html", "rpg_ironhold.html"),
    ("https://nolandda.org/rpg/melderon/index.html", "rpg_melderon.html"),
    ("https://nolandda.org/rpg/melderon_II/index.html", "rpg_melderon_II.html"),
    ("https://nolandda.org/rpg/melderon/characters.html", "rpg_melderon_characters.html"),
    ("https://nolandda.org/rpg/ironhold/rules.html", "rpg_ironhold_rules.html"),
    ("https://nolandda.org/rpg/ironhold/magic.html", "rpg_ironhold_magic.html"),
    ("https://nolandda.org/rpg/melderon/GODS.htm", "rpg_melderon_gods.html"),
    ("https://nolandda.org/rpg/push/index.html", "rpg_push.html"),
    ("https://nolandda.org/rpg/misc/questions.html", "rpg_questions.html"),
    # Photos
    ("https://nolandda.org/photos/", "photos.html"),
    ("https://nolandda.org/photos/creation_museum_2007.05.28/", "photos_creation_museum.html"),
    # PALX
    ("https://nolandda.org/PALX/", "palx.html"),
    ("https://nolandda.org/PALX/members.html", "palx_members.html"),
    ("https://nolandda.org/PALX/adventures.html", "palx_adventures.html"),
    # Old pusite - Purdue pages
    ("https://nolandda.org/pusite/", "pusite.html"),
    ("https://nolandda.org/pusite/about.html", "pusite_about.html"),
    ("https://nolandda.org/pusite/etc.html", "pusite_etc.html"),
    ("https://nolandda.org/pusite/cs490-dsp/wav_format.html", "pusite_dsp_wav.html"),
    # Various writings
    ("https://nolandda.org/history.html", "history.html"),
    ("https://nolandda.org/nato_pa.html", "nato_pa.html"),
    ("https://nolandda.org/sunlight.html", "sunlight.html"),
    ("https://nolandda.org/voyeurism.html", "voyeurism.html"),
    ("https://nolandda.org/ascii.html", "ascii.html"),
    ("https://nolandda.org/colors.html", "colors.html"),
    ("https://nolandda.org/lnf.html", "lnf.html"),
    ("https://nolandda.org/friends.html", "friends.html"),
    ("https://nolandda.org/etc.html", "etc.html"),
    ("https://nolandda.org/tools.html", "tools.html"),
    # Emacs
    ("https://nolandda.org/pusite/emacs.html", "emacs.html"),
    ("https://nolandda.org/pusite/emacs.intro.html", "emacs_intro.html"),
    # Blog posts (qblog)
    ("https://nolandda.org/log/qblog_2007.03.08.19.47.32.html", "blog_2007.html"),
    ("https://nolandda.org/log/qblog_2012.01.12.13.44.37.html", "blog_2012_jan.html"),
    ("https://nolandda.org/log/qblog_2012.10.05.04.23.17.html", "blog_2012_oct.html"),
    ("https://nolandda.org/log/qblog_2012.10.19.22.39.07.html", "blog_2012_oct19.html"),
    ("https://nolandda.org/log/qblog_2013.02.15.17.43.22.html", "blog_2013_feb.html"),
    ("https://nolandda.org/log/qblog_2014.09.16.11.56.42.html", "blog_2014_sep.html"),
    ("https://nolandda.org/log/qblog_2014.10.13.00.47.06.html", "blog_2014_oct.html"),
    ("https://nolandda.org/log/qblog_2014.11.22.21.22.52.html", "blog_2014_nov22.html"),
    ("https://nolandda.org/log/qblog_2014.11.23.00.26.30.html", "blog_2014_nov23.html"),
    ("https://nolandda.org/log/qblog_2014.11.23.02.11.57.html", "blog_2014_nov23b.html"),
]

# Pull each one via Wayback's raw snapshot (id_ prefix skips wrapping)
print(f"Pulling {len(priority_urls)} priority pages from Wayback...")
for url, fname in priority_urls:
    # Find latest snapshot
    cdx_url = f"https://web.archive.org/cdx/search/cdx?url={url}&output=json&limit=-1&filter=statuscode:200"
    try:
        req = urllib.request.Request(cdx_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            cd = json.loads(r.read())
            if not cd or len(cd) < 2:
                print(f"  NO SNAPSHOTS: {url}")
                continue
            # Get latest timestamp
            rows = cd[1:]
            ts = rows[-1][1]
            wayback_url = f"https://web.archive.org/web/{ts}id_/{url}"
            req = urllib.request.Request(wayback_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r2:
                d = r2.read().decode("utf-8", errors="replace")
                outpath = f"{dossier}\\10_full_recon\\nolandda_{fname}"
                open(outpath, "w", encoding="utf-8").write(d)
                print(f"  OK {fname} ({len(d)} chars, ts={ts[:8]})")
    except Exception as e:
        print(f"  ERR {url}: {str(e)[:80]}")
    time.sleep(0.5)

print()
print("Done")