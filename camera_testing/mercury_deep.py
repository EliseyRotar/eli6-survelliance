#!/usr/bin/env python3
import urllib.request
import json
import re

dossier = r"C:\Users\eli6-admin\Documents\eli6-surveillance\dossier_nolandda"

# Try different Mercury Systems endpoints
print("=" * 60)
print("Mercury Systems - various endpoints")
print("=" * 60)
for url in [
    "https://www.mrcy.com/",
    "https://www.mrcy.com/products",
    "https://www.mrcy.com/company",
    "https://www.mrcy.com/company/leadership",
    "https://www.mrcy.com/company/about",
    "https://www.mrcy.com/news",
    "https://www.mrcy.com/news-events",
    "https://www.mrcy.com/news-events/news",
]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            d = r.read().decode("utf-8", errors="replace")
            if "noland" in d.lower():
                print(f"  {url} -> mentions Noland!")
                # Save
                safe = url.replace("https://","").replace("/","_")[:80]
                open(f"{dossier}\\09_employer\\{safe}.html","w",encoding="utf-8").write(d)
            else:
                # Just print title
                m = re.search(r'<title>(.*?)</title>', d)
                t = m.group(1) if m else "?"
                print(f"  {url} -> {t[:80]}")
    except Exception as e:
        print(f"  {url} -> err {str(e)[:80]}")

# Check the archived Dan Noland blog
print()
print("=" * 60)
print("Check nolandda.org for archived blog posts")
print("=" * 60)
# Wayback has 12 other posts beyond the birth one
# Get all URLs that are HTML
try:
    req = urllib.request.Request(
        "https://web.archive.org/cdx/search/cdx?url=nolandda.org&matchType=domain&filter=mimetype:text/html&output=json&from=20180101&to=20261231",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read())
        print(f"  CDX HTML rows: {len(d)}")
        if d:
            header = d[0]
            print(f"  header: {header}")
            # Group by URL
            urls = {}
            for row in d[1:]:
                url = row[2] if len(row) > 2 else "?"
                ts = row[1]
                status = row[4] if len(row) > 4 else "?"
                if status != "200":
                    continue
                if url not in urls or ts > urls[url]:
                    urls[url] = ts
            sorted_urls = sorted(urls.items(), key=lambda x: x[1], reverse=True)
            for url, ts in sorted_urls[:60]:
                print(f"    {ts[:8]} {url}")
except Exception as e:
    print(f"  err: {e}")

# Look for other David Noland search results
print()
print("=" * 60)
print("Search for David Noland on public sites")
print("=" * 60)
# Try archive.org for archived LinkedIn snapshots
try:
    req = urllib.request.Request(
        "https://web.archive.org/cdx/search/cdx?url=linkedin.com/in/*noland*&output=json&limit=20",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read())
        print(f"  LinkedIn noland: {len(d)}")
        for row in d[1:10]:
            print(f"    {row}")
except Exception as e:
    print(f"  err: {e}")

# Check his employer's open positions
print()
print("=" * 60)
print("Mercury Systems job postings for embedded security")
print("=" * 60)
try:
    req = urllib.request.Request("https://jobs.mrcy.com/search/?q=embedded+security",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = r.read().decode("utf-8", errors="replace")
        print(f"  jobs.mrcy.com size: {len(d)}")
        # Find job listings
        titles = re.findall(r'<title>(.*?)</title>', d)
        for t in titles[:5]:
            print(f"  TITLE: {t[:200]}")
        # Look for job titles
        for m in re.finditer(r'<h\d[^>]*>([^<]+(?:Engineer|Developer|Architect|Analyst)[^<]*)</h\d>', d):
            print(f"  JOB: {m.group(1)[:150]}")
except Exception as e:
    print(f"  err: {e}")

# Check opencorpdata.com for Mercury
print()
print("=" * 60)
print("OpenCorporates for Mercury Systems")
print("=" * 60)
try:
    req = urllib.request.Request("https://api.opencorporates.com/v0.4/companies/search?q=Mercury+Systems&jurisdiction_code=us_de",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  Companies: {d.get('results',{}).get('total_count')}")
        for c in d.get("results",{}).get("companies",[])[:5]:
            print(f"  - {c.get('name')} ({c.get('jurisdiction_code')}) {c.get('incorporation_date')}")
except Exception as e:
    print(f"  err: {e}")

# Check Dan's SSH config for mercury-systems credentials
print()
print("=" * 60)
print("Dan's SSH config details (no Mercury Systems hosts)")
print("=" * 60)
ssh_config = open(r"C:\Users\eli6-admin\Documents\eli6-surveillance\camera_testing\nolandda_keys2\ssh-dir\config", "r").read()
print(ssh_config)