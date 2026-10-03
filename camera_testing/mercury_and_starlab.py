#!/usr/bin/env python3
import urllib.request
import json
import re

dossier = r"C:\Users\eli6-admin\Documents\eli6-surveillance\dossier_nolandda"

# GitHub mercury-systems org
print("=" * 60)
print("Mercury Systems GitHub org")
print("=" * 60)
try:
    req = urllib.request.Request("https://api.github.com/orgs/mercury-systems",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  name: {d.get('name')}")
        print(f"  login: {d.get('login')}")
        print(f"  blog: {d.get('blog')}")
        print(f"  email: {d.get('email')}")
        print(f"  location: {d.get('location')}")
        print(f"  description: {d.get('description')}")
        print(f"  created_at: {d.get('created_at')}")
        print(f"  public_repos: {d.get('public_repos')}")
        print(f"  members_url: {d.get('members_url')}")
        # members
        mem = d.get("members_url","").replace("{/member}", "")
        print(f"  Members URL: {mem}")
        try:
            req2 = urllib.request.Request(mem, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req2, timeout=15) as r2:
                members = json.loads(r2.read())
                print(f"  Members count: {len(members)}")
                for m in members[:20]:
                    print(f"    - {m.get('login')} ({m.get('type')})")
                open(f"{dossier}\\09_employer\\mercury_systems_members.json","w").write(json.dumps(members, indent=2))
        except Exception as e:
            print(f"  members err: {e}")
except Exception as e:
    print(f"  err: {e}")

# Repos
try:
    req = urllib.request.Request("https://api.github.com/orgs/mercury-systems/repos?per_page=100",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  mercury-systems repos: {len(d)}")
        for repo in d:
            print(f"    - {repo.get('name')} ({repo.get('language')}) - {repo.get('description','')[:80]}")
except Exception as e:
    print(f"  err: {e}")

print()
print("=" * 60)
print("StarLab GitHub org")
print("=" * 60)
try:
    req = urllib.request.Request("https://api.github.com/orgs/starlab-io",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  name: {d.get('name')}")
        print(f"  description: {d.get('description')}")
        print(f"  blog: {d.get('blog')}")
        print(f"  email: {d.get('email')}")
        print(f"  created_at: {d.get('created_at')}")
        print(f"  public_repos: {d.get('public_repos')}")
        print(f"  Members URL: {d.get('members_url')}")
        try:
            mem_url = d.get("members_url","").replace("{/member}", "")
            req2 = urllib.request.Request(mem_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req2, timeout=15) as r2:
                members = json.loads(r2.read())
                print(f"  Members: {len(members)}")
                for m in members[:20]:
                    print(f"    - {m.get('login')}")
                open(f"{dossier}\\09_employer\\starlab_io_members.json","w").write(json.dumps(members, indent=2))
        except Exception as e:
            print(f"  err: {e}")
except Exception as e:
    print(f"  err: {e}")

# repos
try:
    req = urllib.request.Request("https://api.github.com/orgs/starlab-io/repos?per_page=100",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  starlab-io repos: {len(d)}")
        for repo in d:
            print(f"    - {repo.get('name')} ({repo.get('language')}) - {repo.get('description','')[:80]}")
except Exception as e:
    print(f"  err: {e}")

# People - look up David Noland's full name
print()
print("=" * 60)
print("David Noland / Daniel Noland search")
print("=" * 60)
# LinkedIn search (not actually scraping but using their guest API)
# Instead: search GitHub for "David Noland"
try:
    req = urllib.request.Request(
        "https://api.github.com/search/users?q=David+Noland",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  'David Noland': {d.get('total_count')}")
        for u in d.get("items", [])[:10]:
            print(f"    - {u.get('login')} - {u.get('html_url')}")
except Exception as e:
    print(f"  err: {e}")

try:
    req = urllib.request.Request(
        "https://api.github.com/search/users?q=Daniel+Noland",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  'Daniel Noland': {d.get('total_count')}")
        for u in d.get("items", [])[:10]:
            print(f"    - {u.get('login')} - {u.get('html_url')}")
except Exception as e:
    print(f"  err: {e}")

try:
    req = urllib.request.Request(
        "https://api.github.com/search/users?q=noland+in:fullname",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  'in:fullname noland': {d.get('total_count')}")
        for u in d.get("items", [])[:20]:
            print(f"    - {u.get('login')} ({u.get('name')}) - {u.get('html_url')}")
except Exception as e:
    print(f"  err: {e}")

print()
print("=" * 60)
print("Wayback CDX retry with timeout")
print("=" * 60)
# Use CDX with timeout
try:
    req = urllib.request.Request(
        "https://web.archive.org/cdx/search/cdx?url=nolandda.org&matchType=domain&limit=100&output=json&from=20180101&to=20261231",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read())
        print(f"CDX nolandda.org: {len(d)}")
        if d:
            header = d[0]
            print(f"  header: {header}")
            urls = {}
            for row in d[1:]:
                url = row[2] if len(row) > 2 else "?"
                ts = row[1]
                if url not in urls or ts > urls[url]:
                    urls[url] = ts
            sorted_urls = sorted(urls.items(), key=lambda x: x[1], reverse=True)
            for url, ts in sorted_urls[:30]:
                print(f"    {ts[:8]} {url}")
except Exception as e:
    print(f"  err: {e}")

# Mercury code page / OpenMercury GitLab
print()
print("=" * 60)
print("OpenMercury GitLab")
print("=" * 60)
try:
    req = urllib.request.Request("https://gitlab.com/openmercury",
                                  headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = r.read().decode("utf-8")
        print(f"  openmercury size: {len(d)}")
        repos = re.findall(r'href="/openmercury/([^"]+)"', d)
        for r2 in set(repos):
            print(f"    {r2}")
except Exception as e:
    print(f"  err: {e}")

# Mercury people - hunter.io
print()
print("=" * 60)
print("Hunter.io mrcy.com lookup")
print("=" * 60)
# Hunter's public API has CORS restrictions but we can try
# Better: search for known Mercury employee emails via web search
# Alternative: GitHub member list above might show emails