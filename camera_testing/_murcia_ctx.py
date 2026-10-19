import os
import re
import subprocess
import json

TEMP = os.environ['TEMP']
mmu = open(os.path.join(TEMP, 'mmu.html'), encoding='utf-8', errors='replace').read()

print('--- iframe contexts (600 chars before each) ---')
for m in re.finditer(r'<iframe[^>]+src=["\']([^"\']+)', mmu):
    s = max(0, m.start() - 600)
    ctx = re.sub(r'<[^>]+>', ' ', mmu[s:m.start()])
    ctx = re.sub(r'\s+', ' ', ctx).strip()
    print(' SRC %s' % m.group(1)[:70])
    print('   …%s' % ctx[-260:])

print('\n--- nominatim Puente Tocinos ---')
p = subprocess.run(['curl', '-s', '--max-time', '30', '-A', 'eli6-surveillance-research/1.0',
                    'https://nominatim.openstreetmap.org/search?format=json&countrycodes=es'
                    '&limit=3&q=Puente%20de%20Tocinos%2C%20Murcia'],
                   capture_output=True, timeout=40)
d = json.loads(p.stdout.decode('utf-8', 'replace'))
for x in d:
    print(' ', x.get('display_name', '')[:110], '|', x.get('type'), x.get('lat'), x.get('lon'))
