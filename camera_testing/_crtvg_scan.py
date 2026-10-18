import json
import os
import re

html = open(os.environ['TEMP'] + r'\crtvg_cams.html', encoding='utf-8', errors='replace').read()
print('len', len(html))

imgs = sorted(set(re.findall(r'https?://[^"\'\s<>]+?\.(?:jpg|jpeg|png)[^"\'\s<>]*', html, re.I)))
print('img urls:', len(imgs))
for u in imgs[:40]:
    print('  ', u)

# relative/other image refs
srcs = sorted(set(re.findall(r'["\']([^"\']*(?:camara|cámara|webcam|stream)[^"\']*)["\']', html, re.I)))
print('camara-ish refs:', len(srcs))
for s in srcs[:50]:
    print('  ', s[:180])

# look for embedded json blobs / api endpoints
apis = sorted(set(re.findall(r'["\']([^"\']*(?:api|json|\.action|\.do|service)[^"\']*)["\']', html, re.I)))
print('api-ish refs:', len(apis))
for s in apis[:40]:
    print('  ', s[:180])
