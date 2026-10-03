# Amhilton (Al Hilton, Purdue Chemistry) Fishtank Webcam — Full Forensic Dossier

**URL:** `http://web.ics.purdue.edu/~amhilton/furiousd/webcam.jpg` and `http://web.ics.purdue.edu/~amhilton/tank/tank.jpg`
**Date investigated:** August 21, 2026
**Investigator:** `furiousd_investigation.py` (manual research)

---

## TL;DR

The "Furious D Cam" was a **fish-tank webcam** in the office of Al Hilton, a Purdue University chemistry graduate student (PhD candidate in analytical chemistry, member of the **Garth Simpson Group**, **amhilton = A(lbert) M. Hilton**).

The cam died with its star fish (Furious D, a Red Devil Cichlid) around 2005, but the image stayed on the web server as a 16,010-byte frozen JPEG for at least **another 9 years (2006 → 2014)**. The server itself went 404 sometime between 2012 and 2014. The Wayback Machine captured 67 unique files across 2002-2014.

Al Hilton is **not** Ashley Hilton (a different person with the same username at github.com/amhilton, 2017, 0 repos).

---

## The Person: Al Hilton

### Identity

- **Username:** `amhilton`
- **Real name:** Albert M. Hilton ("particleman" / "Corporal Albert Hilton")
- **Email:** `particleman@purdue.edu`
- **Affiliation:** Purdue University, Department of Chemistry (analytical chemistry PhD program)
- **Lab:** The **Garth Simpson Group** (`chem.purdue.edu/simpson/`) — Al says "the lab I allegedly work in"
- **Period active on web:** 2002 → 2012+ (Wayback captures)
- **Role:** Second-semester General Chemistry TA (2002 era)
- **Note:** "I'm a Ph.D chemistry student and I've *never* worn a lab coat" (2002 `new.html`)

### Evidence
- **bio.html** (2004): Just a poem ("A strange old man stops me, looking out of my deep mirror." -Hitomaro)
- **new.html** (2002 → 2008): Self-written bio with name "Al Hilton"
- **misc.html** (2002): Self-links to "The tragic letters home of Corporal Albert Hilton"
- **misc.htm** (2006-2012): "particleman@purdue.edu" link visible
- **misc/misc.htm 2012**: "About Me -- Possibly coming soon!" (page never finished)
- **Site title:** "Al's Incredible Useless Webpage"

### Hobbies / Interests
- Fish tank (the focal point of the website)
- Nanotechnology research images ("Pictures of Little Things")
- Autograph collection (signed photos of Martha Stewart, James Watson, Chuck Palahniuk, Ravi Shankar, Jeff Corwin, Michael Crichton)
- Photography (multiple gallery pages)
- Web development (FrontPage 5.0, CoffeeCup WebCam 15000)

---

## The Webcam: "Furious D Memorial Camera"

### Technical details
- **First appeared:** November 2004 (CDX first capture 20041114155343)
- **Last working capture:** May 2005 (`webcam.jpg?1094267206823=`, 37,138 bytes)
- **Cam died:** Between December 2004 and September 2006 (Furious D the fish died during this window)
- **Image frozen:** Tank.jpg stays at **16,010 bytes** (SHA1: `9df1250d7cb94e3c`) from 2006 → 2014
- **URLs:**
 - `http://web.ics.purdue.edu/~amhilton/furiousd/webcam.jpg` (640x480)
 - `http://web.ics.purdue.edu/~amhilton/tank/tank.jpg` (640x480)
 - `http://web.ics.purdue.edu/~amhilton/tank/webcam.jpg` (665x509)
- **Page author tool:** CoffeeCup WebCam 15000 (HTML comment in furious.htm and tank.htm)
- **Refresh rate:** 5 seconds (`document.querySelector=rfsh`)
- **Hardware cam:** Likely a Creative Labs or Logitech USB webcam pointed at the fish tank in the Simpson Group lab

### Two cams existed:
1. **`/furiousd/`** — "Furious D Cam" — the main one. Originally pointed at the famous Furious D cichlid. Pointed at "the lab" (`209.216.249.102/~simpson/webcam.jpg` in early 2006) for a brief period.
2. **`/tank/`** — "Fish Tank Field Guide" — the secondary cam with same view but slightly different framing (665×509 vs 640×480).

### Timeline of the fish tank
- **Nov 2004**: Furious D Cam created (`furious.htm` first captured 20041115000552)
- **Dec 2004 → May 2005**: Cam working (2 distinct webcaptures from Wayback: 12,127 + 37,138 bytes — different sizes confirm it was updating)
- **2005**: Furious D (the Red Devil Cichlid) died from "a liver disease or a pH imbalance or something like that" (per tankguide.htm update)
- **2006**: Cam renamed to "Furious D Memorial Camera" — "Furious D is no longer with us, but he awesome webcam lives on. Now with frogs!"
- **2006 → 2014**: Image frozen — server returns same 16,010-byte JPEG
- **2014 → 2018**: Server returns 404 for main and furiousd/; tank/tank.jpg still served (frozen image)
- **2018+**: All amhilton paths return 404 (Purdue decommissioned the `web.ics.purdue.edu` server)

---

## The Fish Roster (from `/misc/tankguide/tankguide.htm`)

| Fish | Species | Origin | Disposition |
|------|---------|--------|-------------|
| **Furious D** | Red Devil Cichlid (`Astronatus ocellatus`) | Named after Simpsons character | Died ~2005 from liver disease / pH imbalance |
| **Captain Sucko** | Plecostomus (`Hypostomus plecostomus`) | Named for sucking algae off glass | Survived |
| **The Chairman** | Koi (`Cyprinus carpio`) | Named after Chairman Kaga (Iron Chef) or Mao | Grew large, voracious |
| **Whatshisname** | Goldfish (`Carassius auratus`) | "Named after our collective lack of imagination" | Survived, paired with Stumpy |
| **Stumpy** | Goldfish | Named for hiding in hollow stump | Survived |
| **Alex** | Goldfish | Maybe Alexis de Tocqueville | Introduced Nov, tolerated by Furious D |
| **Frenchie** | Goldfish (white variety) | All-white variety | Introduced Nov |
| **MudBlood** | Goldfish | Harry Potter reference | "Currently... the smallest fish in the tank" |

> **Key anecdote:** "Some time ago, **Brain** bought 11 small goldfish. Within a few weeks, Furious managed to eat all but two of them."

"Brain" = **Brian Christiansen** of `briandigital.com` (also a Purdue Chemistry alum and friend of Al's — bought the feeder goldfish for Al's tank, which Brian's own iSight cam documented until ~2006).

---

## The Simpson Group Connection

The cam/tank pages link directly to `chem.purdue.edu/simpson/` — Al's research group, run by **Garth J. Simpson** (Purdue Chemistry, analytical/physical chemistry). The growth chart for "The Chairman" the koi is hosted on the Simpson lab's web server: `chem.purdue.edu/simpson/members/Important_Members/growth_chart.JPG`.

This means the fish tank was **physically located in the Simpson Group lab** at Purdue Chemistry, not Al's home.

---

## The Wayback Machine Archive (67 unique URLs)

### Pages
- `index.htm` / `index.html` (multiple snapshots 2002-2014)
- `bio.html` — Haiku poem only
- `biography.html` — Just the word "biography"
- `new.html` — Self-interview ("Roberto's italicized self-interview" was the inspiration)
- `links.htm` — "Links Worth Visiting"
- `qotf.html` — (404, never existed)
- `misc.html` (2002 version, 16KB) — "Cool Fucking Thing of the Week" + random quotes + reading lists
- `misc/misc.htm` (2006-2012 version) — Cleaner misc index
- `images/imaegs.htm` — Photography gallery
- `images/imaegs2.htm`
- `furiousd/furious.htm` — Furious D Cam page
- `tank/` — Tank cam index
- `misc/tankguide/tankguide.htm` — Fish profiles
- `misc/tinythings/tinythings.htm` — Nanotech microscopy images (ecoli, RBC, anthrax, DRAM chips, arthrobacter)
- `misc/auto/auto.htm` — Autograph collection (15+ signed photos)

### Image directories
- `/images/` — Dsc00890.jpg, matrix.jpg, glad2.jpg, alinhell.jpg (Hell, Michigan), cat22.gif, zenpumpkin.gif, bootsy.jpg, chumleys_waltman.jpg, wd.jpg, Capitol_al.jpg, dcbus.gif, work.jpg, rabbit.jpg, thinker_al.jpg, crystal_al2.jpg, particle.jpg (Purdue particle accelerator), philly.jpg, lafayette_al2.jpg, fidel.gif, alice26a.gif
- `/misc/auto/` — stewart.jpg, jstewauto.jpg, jameswatson.jpg, jdw.jpg, watson-crick.jpg, cp_auto.jpg, rshankarauto.jpg, 2004_shankarravi.jpg, jcorwinauto.jpg, jeff-corwin.jpg, I10-57-JurassicPark.jpg, mcrichtonauto.jpg, vine_auto.jpg, nothing.gif, bkapauto.jpg, red_queen.jpg, rid.jpg
- `/misc/tankguide/` — FD.jpg, Sucko.jpg, Chairman.jpg, Whatshisname1.jpg, Stumpy.jpg, alex.jpg, Frenchie.jpg, Mud.jpg, growth_chart.JPG
- `/misc/tinythings/Images/` — ecolibw3d.jpg, rbc.jpg, fo3.jpg, anthrax_1.bmp, arthobacter4b.jpg, ecoligreen.jpg, rbc2.jpg, rbczoom.jpg, DRAM.jpg, ecolipurple.jpg, bsared2.jpg, redlet.jpg

### Wayback CDX summary
- **67 unique URLs** (after collapse by URL key)
- **Date range:** 2002-10-01 → 2014 (last captures 2011-11-07 for furiousd)
- **Status codes:** Mostly 200, with 301 redirects (e.g., `tank` → `tank/`) and some 404s
- **HTTP status:** `web.ics.purdue.edu:80/~amhilton/` — Apache on old Purdue `web.ics.purdue.edu` server

---

## Linked Sites (from `links.htm`)

- "Guess the Dictator or Sit-com Character" — Akinator-style game
- "The Kingdom of Loathing" — KoL (browser game)
- "Stair Dismount" — physics game
- "Purdue Webcams" — directory that included the Furious D cam
- Wikipedia
- Red Meat (webcomic)
- Analytical Chemistry, Science, Nature Biotech, Nature (Saturday morning reading)
- The Washington Post, NY Times, BBC Online
- Science Direct, Web of Science, PubMed, ExPasy (search engines)

---

## Al's Reading List (from misc.html 2002)

**Cool Fucking Thing of the Week (academic paper reviews):**
1. "Patients Admitted to Emergency Services for Drunkenness" (Am J Psychiatry 2001)
2. "Unskilled and Unaware of It" (Kruger & Dunning 1999) — Dunning-Kruger effect
3. "Ultrasonic Velocity in Cheddar Cheese" (J Food Sci 1999)
4. "Magnetic resonance imaging of male and female genitals during coitus" (BMJ 1999)
5. "The collapse of toilets in Glasgow" (Scottish Med J 1993)
6. "Life is sweet: candy consumption and longevity" (BMJ 1998)
7. "Shaken, not stirred: bioanalytical study of the antioxidant activities of martinis" (BMJ 1999)
8. "Toilet Paper Usage in the Former Soviet Bloc"
9. Fun with Java: A Lorenz Attractor
10. The Amazing Vincent Java-Thingy!
11. A Java-Lava Lamp

**Other things referenced:**
- Fan mail / Junk Mail
- Britney Spears' Guide to Semiconductor Physics
- MC Hawking's Crib
- Jesus of the Week
- The Rapture Index
- "The tragic letters home of Corporal Albert Hilton"
- "The History of Mass Spec"
- "Electron Band Structure In Germanium, My Ass"
- www.analtech.com

---

## Image Forensics Summary

| File | Year | Bytes | SHA1[16] | Status |
|------|------|-------|----------|--------|
| `furiousd_webcam_200412.jpg` | Dec 2004 | 12,127 | `95f0a00bdf3e4672` | Real cam frame |
| `furiousd_webcam_200505.jpg` | May 2005 | 37,138 | `0fae0eb3e96f5a71` | Real cam frame |
| `tank_webcam_200505.jpg` | May 2005 | 17,596 | `74f37c86992f0b53` | Real cam frame |
| `tank_jpg_2006.jpg` | 2006 | 16,010 | `9df1250d7cb94e3c` | **FROZEN** |
| `tank_jpg_2008.jpg` | 2008 | 16,010 | `9df1250d7cb94e3c` | **FROZEN** |
| `tank_jpg_2010.jpg` | 2010 | 16,010 | `9df1250d7cb94e3c` | **FROZEN** |
| `tank_jpg_2014.jpg` | 2014 | 16,010 | `9df1250d7cb94e3c` | **FROZEN** |

**Conclusion:** The cam died when Furious D died (~2005), but the webcam JPG stayed on disk for **at least 9 years after the fish died**. The image was probably a single photo of the tank taken after the fish died, not a real live cam.

---

## Related People (Purdue Chemistry network)

| Name | Connection | Evidence |
|------|------------|----------|
| **Roberto** | Friend, mentioned in `new.html` ("Roberto's italicized self-interview is the best way to do these web biography things") | Likely Roberto mention in same dept |
| **Brian ("Brain") Christiansen** | Friend, bought 11 goldfish for the tank | briandigital.com cam (2006-07); both Purdue Chemistry alumni |
| **Garth J. Simpson** | Al's research advisor (Purdue Chem) | chem.purdue.edu/simpson |
| **"particleman"** | Al's email nickname / IRC handle | particleman@purdue.edu |
| **"Corporal Albert Hilton"** | Self-referential nickname (military/family name?) | "The tragic letters home of Corporal Albert Hilton" link |

---

## File Index (in this dossier)

- **Webcam captures (real):** `amhilton_furiousd_webcam_200412.jpg`, `amhilton_furiousd_webcam_200505.jpg`, `amhilton_tank_webcam_200505.jpg`
- **Webcam captures (frozen):** `amhilton_tank_jpg_2006.jpg`, `amhilton_tank_jpg_2014.jpg` (identical SHA1)
- **Fish cam HTML:** `amhilton_furious_wb.html`, `amhilton_furious_2004_v2.html`, `amhilton_tank_index_wb.html`, `amhilton_furiousd_index_wb.html`
- **Fish profiles:** `amhilton_tankguide_2004.html` (Furious D alive), `amhilton_tankguide_correct_wb.html` (Furious D died)
- **Tank guide images:** `amhilton_growth_chart.jpg` (Chairman's growth from `chem.purdue.edu/simpson/`)
- **Bio pages:** `amhilton_new_200210.html`, `amhilton_biography_2004.html`, `amhilton_bio_wb.html`
- **Site pages:** `amhilton_misc_html_200210.html` (16KB original misc), `amhilton_misc_index.html` (2006+ version), `amhilton_imaegs_wb.html`, `amhilton_tinythings_wb.html`, `amhilton_auto_wb.html`, `amhilton_links_2008.html`
- **Misc snapshots:** `amhilton_wb_2003.html`, `amhilton_wb_2004*`, `amhilton_wb_2005*`, `amhilton_wb_2006*`, `amhilton_wb_2007*`, `amhilton_wb_2008*`, `amhilton_wb_2010_main.html`, `amhilton_wb_2012_main.html`, `amhilton_wb_2014.html`
- **CDX data:** `amhilton_cdx.json`, `amhilton_cdx_2000_2004.json`, `amhilton_cdx_collapsed.json`, `amhilton_tank_dir_cdx.json`, `amhilton_furiousd_dir_cdx.json`
- **Github (Ashley Hilton — different person):** `amhilton_github.html`, `amhilton_github_api.json`, `amhilton_github_repos.json`, `amhilton_github_parsed.txt`

---

## Dead Ends / Open Questions

1. **Is Al Hilton still at Purdue?** No clear evidence found. His last `web.ics.purdue.edu` snapshot is 2014. LinkedIn/Purdue directory search would clarify (limited Bing/DDG results — Bing returned Italian locale pages).
2. **What happened to the other fish?** "Brain" (Brian Christiansen) only mentioned in 2004-era tankguide; fate of Sucko/Chairman/Whatshisname/etc. unknown.
3. **Was the cam ever reachable externally?** Probably only on Purdue internal network. The original cam URL `209.216.249.102/~simpson/webcam.jpg` (used briefly in 2006) is also long dead.
4. **Why was the image kept on the server for 9 years?** Likely Al forgot about it; or Purdue sysadmins didn't clean old `/~user/` directories.

---

**End of dossier.**