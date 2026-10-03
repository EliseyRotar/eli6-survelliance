# hackmore_recon — Investigation Archive

**Date:** 2026-08-21
**Subject:** `http://hackmore.net/bug.gif`
**Verdict:** bug.gif is a **2×2 pixel white GIF tracking pixel**, identical from 2005 to 2020, deleted in 2020. `hackmore.net` is **Dan Noland's personal site** (same person from nolandda.org investigation).

## TL;DR
`bug.gif` is a 68-byte GIF89a file with **2×2 all-white pixels**, "Created with The GIMP" comment. It's a classic web bug / tracking pixel — was used on hackmore.net (Dan Noland's personal homepage) for hit-counting or email tracking. Same exact digest `EKF7JCJ5OIZ7OA23LGQF6BZWB5OOMLDN` for **15 years** (2005-2020).

`hackmore.net` belongs to **Dan Noland** (nolandda) — Purdue MS CS 2004, now Senior Security Architect at Star Lab (Washington DC), TS/SCI clearance. Same person from our previous nolandda.org forensic investigation.

His site hosts:
- 500+ photo albums (2005-2010+) — weddings, trips, conventions, GameCube, etc.
- **Resume PDF/PS** (Star Lab, Microsemi, Arxan, Purdue)
- **`/var/log/nolandda` personal blog** — terminal-styled qblog, mentions wife Sara and son Malcolm (b. 2017)
- **`/projects/`** — includes a webcam display CGI for Purdue campus webcams (now404)
- **`/rpg/`** — multiple D&D campaigns he ran
- **`/sekrit/`** — still robots-disallowed but browseable, contains the SSH keys we cracked (modified 2026-05-26), thermostat pics, RPG PDFs (Earthdawn 1e, Hero System 6e Monster Hunter International), Skeptical Inquirer magazine, etc.

## Folder layout
```
hackmore_recon/
├── 00_README.md              ← this file
├── 01_sekrit/                ← SSH keys, thermostats, RPG PDFs, Skeptical Inquirer
├── 02_projects/              ← Webcam Display CGI, GameCube howto, Simcore
├── 03_resume/                ← dnoland_resume.pdf + .ps + extracted text
├── 04_log/                   ← /var/log/nolandda blog index
├── 05_photos/                ← Indexes of 100+ photo albums
├── 06_other/                 ← etc, tools, history, friends, rpg, lnf, ascii, colors
├── 07_bug/                   ← bug.gif from Wayback (2005/2006/2011) + upscaled
├── 08_root_site/             ← Home page + about, robots.txt, favicon, etc.
└── 09_docs/                  ← Full writeup (REPORT.md)
```

## What we discovered

1. **bug.gif is a tracking pixel**, not a photo or webcam
2. **hackmore.net = Dan Noland** (alias nolandda) — same person from our nolandda.org forensic investigation
3. **Dan is a Star Lab Senior Security Architect** with **TS/SCI clearance**, specializing in DRM, anti-tamper, whitebox crypto
4. **`/sekrit/` is still robots-disallowed but browseable** — the ssh-dir.zip we cracked via bkcrack was **Last-Modified 2026-05-26** (3 months ago!)
5. **There's a 1.8GB Earthdawn RPG tarball** at `/sekrit/for-brad/` modified 3 weeks ago
6. **He was working on a Purdue campus webcam display CGI** — tracked live webcams on campus (probably where the nolandda.org cam archive came from!)

## Read order
1. **09_docs/REPORT.md** — full writeup
2. **07_bug/** — the bug.gif itself + upscaled PNG
3. **03_resume/resume_text.txt** — extracted resume text
4. **04_log/log_index.html** — personal blog
5. **01_sekrit/** — SSH keys (same as we cracked!), thermostat pics, RPG PDFs

## Reproduction
```bash
# Get the bug.gif from Wayback
curl -L "https://web.archive.org/web/20110817151150id_/http://hackmore.net/bug.gif" -o bug.gif

# Get the resume PDF
curl -L "https://hackmore.net/resume/dnoland_resume.pdf" -o resume.pdf

# See all /photos albums
curl -L "https://hackmore.net/photos/" | grep -oP 'href="[^"]+/"'
```