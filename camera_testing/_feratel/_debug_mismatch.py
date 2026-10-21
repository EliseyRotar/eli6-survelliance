import json, sys
sys.path.insert(0, 'camera_testing\\_feratel')
from _enumerate import fetch, parse
import re, html as H, json as J

url = 'https://www.feratel.com/en/webcams/andorra/encamp/encamp-cortals-15090'
raw = fetch(url)
rec = parse(url, raw)
print('main cam:', (rec.get('cam') or {}).get('camId'))
print('related ids:', [r['camId'] for r in rec.get('related', [])])
# all camId occurrences in raw (escaped)
ids = re.findall(r'camId&quot;:\[0,&quot;(\d+)&quot;\]', raw)
print('raw camId islands:', ids)
# is there a non-escaped camId?
ids2 = re.findall(r'"camId":\[0,"(\d+)"\]', raw)
print('raw camId unescaped:', ids2)
# check where 15090 appears
for m in list(re.finditer('15090', raw))[:6]:
    print('ctx:', repr(raw[max(0, m.start()-150):m.start()+60]))
