#!/usr/bin/env python3
import json
import urllib.request
import re

dossier = r"C:\Users\eli6-admin\Documents\eli6-surveillance\dossier_nolandda"

def fetch(url, path, hdrs=None):
    try:
        req = urllib.request.Request(url, headers=hdrs or {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read().decode("utf-8", errors="replace")
            open(path, "w", encoding="utf-8").write(data)
            return data
    except Exception as e:
        return f"ERROR: {e}"

print("=" * 70)
print("WordPress blog")
print("=" * 70)
wp = fetch("https://nolandda.wordpress.com", f"{dossier}\\10_full_recon\\wordpress.html")
print(f"Size: {len(wp)}")
# Extract titles and posts
for m in re.finditer(r'<h[1-3][^>]*class="entry-title"[^>]*>(.*?)</h[1-3]>', wp, re.DOTALL):
    title = re.sub(r'<[^>]+>', '', m.group(1)).strip()
    print(f"  POST: {title}")
# Look for about/profile mentions
for m in re.finditer(r'<meta\s+(?:name|property)="([^"]+)"\s+content="([^"]+)"', wp):
    if any(k in m.group(1).lower() for k in ["description", "title", "author"]):
        print(f"  META {m.group(1)}: {m.group(2)[:200]}")

print()
print("=" * 70)
print("PyPI")
print("=" * 70)
pypi = fetch("https://pypi.org/user/nolandda/", f"{dossier}\\10_full_recon\\pypi.html")
print(f"Size: {len(pypi)}")
# Project links
for m in re.finditer(r'<a[^>]+href="(/project/([^"]+))"', pypi):
    print(f"  PROJECT: {m.group(2)}")

print()
print("=" * 70)
print("StackOverflow API")
print("=" * 70)
so = fetch("https://api.stackexchange.com/2.3/users/294999?site=stackoverflow",
           f"{dossier}\\10_full_recon\\so_api.json")
try:
    j = json.loads(so)
    items = j.get("items", [])
    if items:
        u = items[0]
        print(f"  display_name: {u.get('display_name')}")
        print(f"  link: {u.get('link')}")
        print(f"  reputation: {u.get('reputation')}")
        print(f"  location: {u.get('location')}")
        print(f"  website_url: {u.get('website_url')}")
        print(f"  about_me: {u.get('about_me')}")
        print(f"  creation_date: {u.get('creation_date')}")
        print(f"  last_access_date: {u.get('last_access_date')}")
    else:
        print(f"  No user. Error: {j.get('error_message', '?')}")
except Exception as e:
    print(f"  Parse: {e}")
    print(so[:500])

print()
print("=" * 70)
print("DockerHub repos")
print("=" * 70)
dh = fetch("https://hub.docker.com/v2/users/nolandda/repos/?page_size=100",
           f"{dossier}\\10_full_recon\\dockerhub_repos.json")
try:
    j = json.loads(dh)
    print(f"  count: {j.get('count')}")
    for r in j.get("results", []):
        print(f"  - {r.get('namespace')}/{r.get('name')} ({r.get('star_count')} stars, last_updated={r.get('last_updated')})")
except Exception as e:
    print(f"  Parse: {e}")
    print(dh[:300])

print()
print("=" * 70)
print("Blogger content")
print("=" * 70)
bg = fetch("https://nolandda.blogspot.com", f"{dossier}\\10_full_recon\\blogger.html")
print(f"Size: {len(bg)}")
# Blogger posts have class="post-title"
for m in re.finditer(r'class="post-title[^"]*"[^>]*>(.*?)</(?:h\d|div)', bg, re.DOTALL):
    t = re.sub(r'<[^>]+>', '', m.group(1)).strip()
    if t:
        print(f"  POST: {t}")
# Try alt pattern
for m in re.finditer(r'<h\d[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</h\d>', bg, re.DOTALL):
    t = re.sub(r'<[^>]+>', '', m.group(1)).strip()
    if t and "post" in m.group(0).lower():
        print(f"  ALT: {t}")
# Post dates
for m in re.finditer(r'dateline[^>]*>([^<]+)', bg):
    print(f"  DATE: {m.group(1).strip()[:60]}")

print()
print("=" * 70)
print("SourceHut")
print("=" * 70)
srht = fetch("https://sr.ht/~nolandda/", f"{dossier}\\10_full_recon\\srht.html")
print(f"Size: {len(srht)}")
# Find user info
for m in re.finditer(r'<title>(.*?)</title>', srht):
    print(f"  TITLE: {m.group(1)[:200]}")
# 404 or not?
if "Not Found" in srht or "404" in srht[:3000]:
    print("  → 404 NOT FOUND")

print()
print("=" * 70)
print("Codeberg")
print("=" * 70)
cb = fetch("https://codeberg.org/nolandda", f"{dossier}\\10_full_recon\\codeberg.html")
print(f"Size: {len(cb)}")
# Codeberg repos
for m in re.finditer(r'<a[^>]+href="/nolandda/([^"]+)"[^>]*>\s*(.*?)\s*</a>', cb, re.DOTALL):
    name = m.group(1).strip()
    desc = re.sub(r'<[^>]+>', '', m.group(2)).strip()
    if name and not name.startswith("?"):
        print(f"  REPO: {name} - {desc[:80]}")

print()
print("=" * 70)
print("GitLab user API")
print("=" * 70)
gl = fetch("https://gitlab.com/api/v4/users?username=nolandda",
           f"{dossier}\\10_full_recon\\gitlab_api.json")
try:
    j = json.loads(gl)
    if isinstance(j, list) and j:
        u = j[0]
        print(f"  id: {u.get('id')}")
        print(f"  username: {u.get('username')}")
        print(f"  name: {u.get('name')}")
        print(f"  bio: {u.get('bio')}")
        print(f"  location: {u.get('location')}")
        print(f"  website: {u.get('website')}")
        print(f"  twitter: {u.get('twitter')}")
        print(f"  public_email: {u.get('public_email')}")
        print(f"  created_at: {u.get('created_at')}")
        print(f"  last_sign_in_at: {u.get('last_sign_in_at')}")
        print(f"  last_activity_on: {u.get('last_activity_on')}")
    else:
        print("  No user.")
except Exception as e:
    print(f"  Parse: {e}")

# Projects
glp = fetch("https://gitlab.com/api/v4/users/13673213/projects?per_page=100",
            f"{dossier}\\10_full_recon\\gitlab_projects.json")
try:
    j = json.loads(glp)
    print(f"  Projects: {len(j) if isinstance(j, list) else 'err'}")
    for p in (j if isinstance(j, list) else []):
        print(f"  - {p.get('path_with_namespace')} ({p.get('visibility')}, last_activity={p.get('last_activity_at')[:10] if p.get('last_activity_at') else '?'})")
except Exception as e:
    print(f"  Parse: {e}")