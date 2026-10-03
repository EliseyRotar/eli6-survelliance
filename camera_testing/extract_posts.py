#!/usr/bin/env python3
import re

# Blogger posts
print("=" * 60)
print("BLOGGER POSTS")
print("=" * 60)
with open(r"C:\Users\eli6-admin\Documents\eli6-surveillance\recon\dossier_nolandda\10_full_recon\blogger.html", encoding="utf-8") as f:
    bg = f.read()
print(f"Size: {len(bg)}")
# Find h3 posts (Blogger default)
for m in re.finditer(r'<h3[^>]*class="post-title[^"]*"[^>]*>(.*?)</h3>', bg, re.DOTALL):
    t = re.sub(r'<[^>]+>', '', m.group(1)).strip()
    if t:
        print(f"  POST: {t}")
# Try h2 also
for m in re.finditer(r'<h2[^>]*class="post-title[^"]*"[^>]*>(.*?)</h2>', bg, re.DOTALL):
    t = re.sub(r'<[^>]+>', '', m.group(1)).strip()
    if t:
        print(f"  POST2: {t}")
# Generic - find <a> within post context
posts = re.findall(r'<a[^>]+href="([^"]*blogspot[^"]*?\d{4}/\d{2}/[^"]+)"[^>]*>([^<]+)</a>', bg)
for url, title in posts[:30]:
    print(f"  POST URL: {url[:80]}")
    print(f"  TITLE: {title.strip()[:120]}")

# Profile/about
m = re.search(r'<title>(.*?)</title>', bg)
if m:
    print(f"  TITLE: {m.group(1)[:200]}")
# Blogger Profile
m = re.search(r'profile\.blogger\.com/([^/"\']+)', bg)
if m:
    print(f"  BLOGGER_PROFILE: {m.group(1)}")

# Search for dates
dates = re.findall(r'(\w+ \d+, \d{4})', bg)
print(f"  DATES_FOUND: {set(dates)}")

print()
print("=" * 60)
print("DOCKERHUB HTML")
print("=" * 60)
with open(r"C:\Users\eli6-admin\Documents\eli6-surveillance\recon\dossier_nolandda\10_full_recon\dockerhub_user.html", encoding="utf-8") as f:
    dh = f.read()
print(f"Size: {len(dh)}")
# Look for repositories
m = re.search(r'<title>(.*?)</title>', dh)
if m:
    print(f"  TITLE: {m.group(1)}")
# Count docker repo links
repos = re.findall(r'href="(/r/[^/"]+/([^"]+))"', dh)
print(f"  Repos in HTML: {len(repos)}")
for url, name in repos[:20]:
    print(f"  - https://hub.docker.com{url}")

# Look for the "no repos" message
if "no public repositories" in dh.lower():
    print("  → 'no public repositories' found")
if "is not a registered user" in dh.lower():
    print("  → 'not a registered user' found")