"""Watch what HTTP requests a real browser makes to TV.

Since we can't run a real browser, we'll inspect the JS bundle for clues about
which Firestore calls are made after signin.
"""
import urllib.request, socket, re
socket.setdefaulttimeout(30)

# Get main api.js
req = urllib.request.Request('https://trafficvision.live/assets/api-CmVqwtkf.js', headers={'User-Agent': 'Mozilla/5.0'})
r = urllib.request.urlopen(req, timeout=30)
js = r.read().decode('utf-8', errors='replace')

# Look for collection refs
collections = set(re.findall(r'collection\([\"\']([^\"\']+)[\"\']', js))
print('Collection refs in api.js:', collections)

# Look for Firestore imports/calls
firestore_funcs = set(re.findall(r'(?:getDocs|getDoc|onSnapshot|query|where|orderBy|limit|startAfter|addDoc|setDoc|updateDoc|deleteDoc|doc)\b', js))
print('Firestore funcs:', firestore_funcs)

# Look for query patterns
queries = re.findall(r'where\([\"\']([^\"\']+)[\"\'].*?==.*?[\"\']([^\"\']+)[\"\']', js)
print('Where queries:', queries[:20])

# Look for collection names mentioned anywhere
all_coll_refs = set(re.findall(r'[\"\'](\w+)[\"\']\s*:\s*[\"\'](\w+)[\"\']', js))
coll_refs = [c for c in all_coll_refs if c[1] in ['cameras','feeds','catalog','catalogues','sources','users','favorites','bookmarks','routes','collections','previewStatus']]
print('Collection name refs:', coll_refs[:30])
