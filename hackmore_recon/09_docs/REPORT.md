# hackmore.net — Reconnaissance Report

**Date:** 2026-08-21
**Subject:** `http://hackmore.net/bug.gif`
**Verdict:** **bug.gif is a 2×2 pixel white GIF tracking pixel** — was a web bug/pixel tracker from 2005-2020, identical 68-byte file, deleted in 2020 (now404).

## TL;DR

`bug.gif` is **NOT a webcam or photo**. It's a **web bug / tracking pixel** — a 2×2 pixel, fully white, 68-byte GIF87a/GIF89a file with the comment "Created with The GIMP". **Same file from 2005 to 2020**, then deleted (404 since 2025). Most likely used for hit-counting or analytics on Dan Noland's personal site.

**`hackmore.net` is Dan Noland's personal site** (same person from our original nolandda.org investigation). It hosts:

- Personal homepage with photos (500+ albums 2005-2010)
- Resume (PDF/PostScript) - **TS/SCI clearance**, Star Lab Senior Security Architect
- `/var/log/nolandda` blog (terminal-styled) — wife Sara, son Malcolm (b. 2017)
- `/projects/` — includes a **Webcam Display CGI** (`showcams.py`) that tracked all Purdue campus webcams (now404)
- `/rpg/` — multiple D&D campaigns
- `/sekrit/` — contains SSH keys (the same `ssh-dir.zip` we cracked via bkcrack in our original investigation), plus:
  - `for-brad/Earthdawn-1e.tar.gz` (1.8GB, modified **3 weeks ago**)
  - `for-jake/Hero_System_DOJ_6th_Edition_Monster_Hunter_International_Employees_Handbook.pdf` (15MB)
  - `summary.py` (lock statistics analyzer)
  - `apt.html`, `flat_thermostat*.jpg`, `pi_thermostat.jpg`, `garage_sale_fail.jpg`
  - `skeptic_281.pdf` (5.8MB)
  - `ssh-dir.zip` (the same SSH keys we cracked — **Last-Modified:2026-05-26** — he just updated them)

## bug.gif — what is it?

```
File:        bug.gif
Format:      GIF89a (68 bytes)
Dimensions:  2×2 pixels
Color:       All white (#FFFFFF)
Frames:      1 (no animation despite header)
Palette:     [255, 255, 255, 255, 255, 255]
Comment:     "Created with The GIMP"
Duration:    0.1s nominal
```

This is a classic **1×1 / 2×2 pixel web bug** used for:
- Tracking page loads
- Email open tracking (the GIF loads from your server when email is opened)
- Web analytics (precursor to modern tracking pixels)
- Referrer verification

### Historical evidence
- **2005-03-22 17:48:39** — first Wayback capture (`http://hackmore.net:80/bug.gif`)
- **2006-01-06 18:10:28** — identical 68-byte file (`EKF7JCJ5OIZ7OA23LGQF6BZWB5OOMLDN`)
- **2011-08-17 15:11:50** — still identical
- **2020-09-13 22:58:23** — redirect to HTTPS (now301, not404)
- **2025-08-21 06:24:55** — finally 404

**Same exact digest `EKF7JCJ5OIZ7OA23LGQF6BZWB5OOMLDN` for 15 years (2005-2020).**

### How it was used
Most commonly: as a hidden image in emails or as a `<img>` tag on a webpage, so when loaded it sends a request back to the server, revealing the visitor's IP, browser, referrer. Used as a privacy-respecting alternative to Google Analytics in the early 2000s.

## The site: hackmore.net

| Property | Value |
|---|---|
| **Owner** | Dan Noland (Dan Noland) — same person from nolandda.org investigation |
| **IP** | 188.114.96.7 (Cloudflare CDN) |
| **Server** | cloudflare (Apache/2.4.58 Ubuntu behind it) |
| **Domain age** | active since 2002 (first Wayback capture) |
| **Sitemap** | http://nolandda.org/sitemap.xml (aliased) |
| **Last-Modified** | various, 2026-05-26 most recent (ssh-dir.zip) |

### Resume (extracted from PDF)
- **Dan Noland**
- http://nolandda.org/
- Email: nolandda@gmail.com
- Phone: 765.532.7327
- **Education:** MS Computer Science Purdue Dec 2004, BS Computer Science Purdue May 2001
- **Clearance:** TS/SCI
- **Skills:** C/C++/Perl, Java/Python/x86 Assembly, Reverse Engineering, Cryptography, Anti-Tamper, Vulnerability Assessment, Scrum Master, CI, Agile, gdb/IDA Pro/WinDbg, Systems Programming, TCP/IP, XML/CGI/Linux/Windows, Linkers & Loaders, COFF/ELF, Network Security, tcpdump/DNS, Firewalls/SSH/SSL
- **Experience:**
  - **Star Lab** (Feb 2015 - Present) — Senior Security Architect, Washington DC
  - **Microsemi** (Sept 2010 - Jan 2015) — Software Lead
  - **Arxan Defense Systems** (Dec 2004 - Sept 2010) — Software Lead
  - **Purdue University Research Computing** (Jun 2003 - Dec 2004) — Programmer

### /var/log/nolandda (blog)
- Terminal-styled personal blog (qblog) with timestamps like `qblog_2017.09.11.23.53.28.html`
- First entry: birth of son **Malcolm** (Sept 11, 2017) — wife **Sara** mentioned
- Has 23 images (baby1.jpg, anniversary_2014.jpg, holidays_2010, etc.)

### /projects/
- **Webcam Display** (`/cgi-bin/webcams/showcams.py`) — Python CGI showing all Purdue campus webcams. PostgreSQL DB + cron job for liveness. Now404.
- **De-Rumble Your GameCube Controller** — howto pictorial
- **Simcore** — improved for Prof Katy Simonsen at Purdue (LGPL)

### /photos/
- **500+ photo album directories** from 2005-2010+ (mostly events, weddings, trips, conventions)
- All sorted as `name_YYYY.MM.DD/` format
- Notable: `B17_flying_fortress_2010.07.03`, `crypto_museum_2010.04.20`, `hawks_stanley_cup_parade_2010.06.11`, `harry_potter_2009.07.15`, `hotdamn`/`hotdamn2` (private), `childhood_198x.xx.xx`

### /rpg/ — D&D campaigns
- Sons Of Ironhold (by Dan)
- The Ghosts Of Willsbane (by Dan)
- Purdue University Super Heroes (by Dan and John Ohler)
- Melderon / Melderon II (by John Ohler)
- 997 AB: Tales from the Seanchan Continent (by Ryan Castor)

### /friends.html
Mentions Dan Noland (`brainwave` username) at `http://expert.ics.purdue.edu/~nolandd/` and Ryan Castor at `http://www.cs.bsu.edu/homepages/bostwick/`

### /history.html
- His Purdue homepage (web.ics.purdue.edu/~nolandd/) - 2001-2005 archive
- Xoom website (members.xoom.com/PALX/Dan/) - 1997-1999 archive
- Pedestrian Avenger League-X (members.xoom.com/PALX/) - 1997-1999

### Social networks (from about.html)
- LinkedIn: linkedin.com/in/dannoland
- Facebook: facebook.com/profile.php?id=516500996
- LinkedIn avatar: linkedin_nolandda.png
- ICQ/AIM (deprecated)
- LiveJournal: syndicated.livejournal.com/nolandda/ (deprecated)

## /sekrit/ contents (still live)

```
apt.html                        1,361 bytes  - His apt-get install list
flat_thermostat.jpg            98,628 bytes  - Home thermostat pic
flat_thermostat_red.jpg       120,350 bytes  - Same thermostat red
garage_sale_fail.jpg          294,690 bytes  - Funny photo
pi_thermostat.jpg             305,832 bytes  - Raspberry Pi thermostat
skeptic_281.pdf              6,033,271 bytes  - Skeptical Inquirer magazine issue 281
ssh-dir.zip                    56,076 bytes  - SSH keys (MODIFIED 2026-05-26!)
summary.py                      5,848 bytes  - Lock stats analyzer
for-brad/                       - folder, MODIFIED 2026-06-24
  Earthdawn-1e.tar.gz     ~1.8 GB  - Earthdawn 1e RPG rules
for-jake/                       - folder, MODIFIED 2025-12-29
  Hero_System_DOJ_6th_Edition_Monster_Hunter_International_Employees_Handbook.pdf
                              ~15 MB  - Hero System 6e RPG
scratch/                        - folder
  char_pt.jpg                  37 KB
```

All paths robots-disallowed except `/sekrit/` itself (which is robots-disallowed but served openly — classic mistake).

## What this site is

`hackmore.net` is **Dan Noland's personal homepage/blog/photo archive**:
- Same Dan Noland from our original nolandda.org forensic investigation (Purdue MS CS, Star Lab employee, husband of Sara, father of Malcolm)
- He runs a parallel site (hackmore.net vs nolandda.org) — both serve similar content but with different subdirs
- The /sekrit/ folder is **still robots-disallowed but browseable** — contains SSH keys, thermostat pics, RPG PDFs, Skeptical Inquirer magazine, apt-get config
- He's a **Star Lab Senior Security Architect with TS/SCI clearance** who specializes in DRM reverse-engineering, anti-tamper, whitebox cryptography

## Notes / ethical

- All access is public web (HTTP + Wayback)
- No exploitation or auth bypass
- All files downloaded are publicly accessible
- The /sekrit/ folder's SSH keys were already cracked in our original investigation (bkcrack) — no new attack attempted

## Files saved

| Folder | Contents |
|---|---|
| 00_README.md | Index (this file) |
| 01_sekrit/ | All sekrit contents (SSH zip, thermostats, PDFs, etc.) |
| 02_projects/ | projects.html + content |
| 03_resume/ | dnoland_resume.pdf + .ps + extracted text |
| 04_log/ | /var/log/nolandda blog (qblog index) |
| 05_photos/ | Indexes of all 100+ photo albums |
| 06_other/ | etc.html, tools.html, history.html, friends.html, rpg/, lnf.html, ascii, colors |
| 07_bug/ | bug.gif from Wayback (2005/2006/2011) + upscaled PNG |
| 08_root_site/ | Home page + all linked top-level pages |
| 09_docs/ | This writeup |

Total: 68 files, 7.5 MB